#load the required libraries
from ctypes import *
from dwfconstants import *
import math
import time
import matplotlib.pyplot as plt
import sys
import numpy as np
import csv
import os
import multiprocessing 
import save_functions as sf

if sys.platform.startswith("win"):
    dwf = cdll.dwf
elif sys.platform.startswith("darwin"):
    dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
else:
    dwf = cdll.LoadLibrary("libdwf.so")


if __name__ == "__main__": 
    #declare the handle to the oscilloscope
    hdwf = c_int()
    #declare a varible to monitor the oscilloscope status (Done, Triggered...)
    sts = c_byte()

    #Get version information about waveforms
    version = create_string_buffer(16)
    dwf.FDwfGetVersion(version)
    print("DWF Version: "+str(version.value))

    #Open a device with a given ip adres
    print("Opening device of ip 10.226.35.165")
    szOpt = c_char_p(b"ip:10.226.35.165\nuser:digilent\npass:digilent\nsecure:1")
    dwf.FDwfDeviceOpenEx(szOpt, byref(hdwf))

    #Check if the oscilloscope is open and stop the program if not
    if hdwf.value == hdwfNone.value:
        szError = create_string_buffer(512)
        dwf.FDwfGetLastErrorMsg(szError);
        print("failed to open device\n"+str(szError.value))
        quit()

    dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0)) # 0 = the device will only be configured when FDwf###Configure is called


    """
    CONFIG FOR SUNSETS:
    2000 samples at 100e6 Hz rate ~ 20us

    SWB_CH: 200 mV total, ~100 mV offset at 7kV
    SWT_CH: 500 mV total, ~200 mV offset at 7kV
    CH1, Trigger: 750 mV total,  NIM(500 mV negative pulse signal), 0 V offset
    """

    #declare the parameters for the adquisition
    save_csv = True # Whether to save the data in a csv or not
    nSamples = 2000 #number of data points to take each triggered adquisition
    hzRate = 100e6 #Adquisition frequency in Hz

    #Change parameters into c_types to interact with the scope, define arrays to sabe data "rgdSamples"
    hzAcq = c_double(hzRate)
    rgdSamples_channel1 = (c_double*nSamples)()
    rgdSamples_channel2 = (c_double*nSamples)()
    rgdSamples_channel3 = (c_double*nSamples)()
    rgdSamples_channel4 = (c_double*nSamples)()

    #set up acquisition parameters
    dwf.FDwfAnalogInFrequencySet(hdwf, hzAcq) #Adquisition frequency
    dwf.FDwfAnalogInBufferSizeSet(hdwf, c_int(nSamples)) #Number of samples to take
    dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(-1), c_int(1)) #Enable all channels to take data (-1 for all)
    dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(-1), c_double(5)) #Set the range of the channels to 5 V by default
    dwf.FDwfAnalogInChannelFilterSet(hdwf, c_int(-1), c_int(3)) #Set the adquisition mode to filterAverageFit which stores the average of N ADC conversions and fits to get more precise results

    #Change range channel by channel
    dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(0), c_double(1)) #Channel 1
    dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(1), c_double(1)) #Channel 2
    dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(2), c_double(1)) #Channel 3
    dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(3), c_double(1)) #Channel 4

    #Change offset channel by channel
    dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(0), c_double(0)) #Channel 1
    dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(1), c_double(0)) #Channel 2
    dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(2), c_double(0)) #Channel 3 
    dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(3), c_double(0)) #Channel 4

    #Set up trigger configuration
    dwf.FDwfAnalogInTriggerAutoTimeoutSet(hdwf, c_double(0)) #Disable auto trigger after time without a trigger
    dwf.FDwfAnalogInTriggerSourceSet(hdwf, trigsrcDetectorAnalogIn) #Set the trigger to one of the analog channels
    dwf.FDwfAnalogInTriggerTypeSet(hdwf, trigtypeEdge) #Set to trigger on an Edge
    dwf.FDwfAnalogInTriggerChannelSet(hdwf, c_int(0)) #Set the trigger channel to channel 1
    dwf.FDwfAnalogInTriggerLevelSet(hdwf, c_double(-0.200)) # Set the trigger level
    dwf.FDwfAnalogInTriggerConditionSet(hdwf, DwfTriggerSlopeFall)  #Set to trigger on a Falling edge

    #dwf.FDwfAnalogInTriggerPositionSet(hdwf, c_double(0.5*nSamples/hzRate)) #To set the trigger point to the start
    dwf.FDwfAnalogInTriggerPositionSet(hdwf, c_double(0)) #Set the offset of the trigger to 0 (trigger in the middle)

    # wait at least 2 seconds with Analog Discovery for the offset to stabilize, before the first reading after device open or offset/range change
    time.sleep(2)

    #Start the oscilloscope to take acquisitions
    print("Starting repeated acquisitions")
    dwf.FDwfAnalogInConfigure(hdwf, c_int(1), c_int(1))

    #Define the saving directory and time related variables
    saving_directory = "/daq/scratch/FC_mini_osc/triggered_data/"
    csv_name = saving_directory + "trigger_"
    sec = c_uint(1)
    tick = c_uint(1)
    ticksec = c_uint(1)


    # creating multiprocessing Queue for saving the data
    q1 = multiprocessing.Queue(-1) 
    
    #Make a loop to continously check for triggered adquisitions, if crt^c is pressed the adquisition will stop
    try:
        while True:
            #Create the proccess to save to the csv (p1) 
            p1 = multiprocessing.Process(target=sf.save_trigger, args=(csv_name, hzRate, sec, tick, ticksec ,q1,)) 
            
            #Make the adquisition
            while True:
                dwf.FDwfAnalogInStatus(hdwf, c_int(1), byref(sts))
                if sts.value == DwfStateDone.value :
                    break
                time.sleep(0.001)

             #Fetch the data from the scope to the rdgSamples vectors
            dwf.FDwfAnalogInStatusData(hdwf, 0, rgdSamples_channel1, nSamples) #Channel 1 data
            dwf.FDwfAnalogInStatusData(hdwf, 1, rgdSamples_channel2, nSamples) #Channel 2 data
            dwf.FDwfAnalogInStatusData(hdwf, 2, rgdSamples_channel3, nSamples) #Channel 3 data
            dwf.FDwfAnalogInStatusData(hdwf, 3, rgdSamples_channel4, nSamples) #Channel 4 data
            
            #Get When the trigger happened
            dwf.FDwfAnalogInStatusTime(hdwf, byref(sec), byref(tick), byref(ticksec))   
            
            #Convert the data froma  c_type vector to a array of python lits (for saving and processing)
            py_data = [list(rgdSamples_channel1), list(rgdSamples_channel2), list(rgdSamples_channel3), list(rgdSamples_channel4)] 
            
            #Save the .csv file
            if save_csv:
                q1.put(py_data)
                p1.start()
            

    except KeyboardInterrupt:
        #When the program stops reset the scope configurations and close the device
        print("Acquisition stopped by user")
        dwf.FDwfAnalogOutReset(hdwf, c_int(0))
        dwf.FDwfDeviceCloseAll()

