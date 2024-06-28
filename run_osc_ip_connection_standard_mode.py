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

    #declare the parameters for the adquisition
    adq_frec = 100 # Adquisition frequency in Hz
    down_spl = 10 # Downsapling for the dB, save 1/down_spl of data to slow control DB
    record_time = 10 # Duration of the adquisition in seconds

    save_csv = True # Whether to save the data in a csv or not
    write_db = False #Whether to write data into the db or not

    #Change parameters into c_types to interact with the scope, define arrays to save data "rdgSamples", calculate number of samples
    nSamples = int(record_time * adq_frec)
    hzAcq = c_double(adq_frec) 
    rgdSamples_channel1 = (c_double*nSamples)()
    rgdSamples_channel2 = (c_double*nSamples)()
    rgdSamples_channel3 = (c_double*nSamples)()
    rgdSamples_channel4 = (c_double*nSamples)()

    #Check if number of samples exceed oscilloscope buffer
    if nSamples > 128000000.:
        print("Number of samples exceed oscilloscope buffer, lower the time, frequency or use Record function")
        quit()

    #Get version information about waveforms
    version = create_string_buffer(16)
    dwf.FDwfGetVersion(version)
    print("DWF Version: "+str(version.value))
    dwf.FDwfParamSet(DwfParamOnClose, c_int(0)) # 0 = run, 1 = stop, 2 = shutdown

    #Open a device with a given ip adres
    print("Opening device with IP")
    szOpt = c_char_p(b"ip:10.226.35.165\nuser:digilent\npass:digilent\nsecure:1")
    dwf.FDwfDeviceOpenEx(szOpt, byref(hdwf))

    #Check if the oscilloscope is open and stop the program if not
    if hdwf.value == hdwfNone.value:
        szerr = create_string_buffer(512)
        dwf.FDwfGetLastErrorMsg(szerr)
        print(str(szerr.value))
        print("failed to open device")
        quit()

    dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0)) # 0 = the device will only be configured when FDwf###Configure is called

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


    #wait at least 2 seconds for the scope to stabilize
    time.sleep(2)

    #Tell the scope to start the adquisitions
    print("Starting repeated acquisitions")
    dwf.FDwfAnalogInConfigure(hdwf, c_int(1), c_int(1))

    #define the directory in which to save data
    saving_directory = "/daq/scratch/FC_mini_osc/monitoring_data/"

    # create multiprocessing Queue for data saving and sending to the db
    q1 = multiprocessing.Queue(-1) 
    q2 = multiprocessing.Queue(-1)

    #Make a loop to do continous adquisition, if crt^c is pressed the adquisition will stop
    try:
        while True:
            # Record the time it takes to do the adquisition
            start_time = time.time()
            print(f"Starting acquisition {start_time}")

            #Define the name of the csv file 
            csv_name = saving_directory + "oscilloscope_data_" + str(start_time).replace(".", "-" ) + "_ALL.csv"
            
            # create the proccess to save to the csv (p1) and send data to the db (p2)
            p1 = multiprocessing.Process(target=sf.save_multi, args=(csv_name, adq_frec, q1,)) 
            p2 = multiprocessing.Process(target=sf.write_db, args=(start_time, adq_frec, down_spl, q2,))
            
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

            #Convert the data froma  c_type vector to a array of python lits (for saving and processing)
            py_data = [list(rgdSamples_channel1), list(rgdSamples_channel2), list(rgdSamples_channel3), list(rgdSamples_channel4)]
            
            #Save the .csv file
            if save_csv:
                q1.put(py_data)
                p1.start()
                
            #Send data to the db
            if write_db:
                q2.put(py_data)
                p2.start()
                
            end_time = time.time()
            
            # Print the time it took to make 1 adquisition
            end_time = time.time()
            print(f"Acquisition {start_time} completed")
            print("End time:", end_time - start_time)


    except KeyboardInterrupt:
        #When the program stops reset the scope configurations and close the device
        print("Acquisition stopped by user")
        dwf.FDwfAnalogOutReset(hdwf, c_int(0))
        dwf.FDwfDeviceCloseAll()
        

