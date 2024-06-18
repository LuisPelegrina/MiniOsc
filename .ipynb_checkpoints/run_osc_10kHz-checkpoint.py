#load things
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

#declare ctype variables
hdwf = c_int()
sts = c_byte()

adq_frec = 10000
hzAcq = c_double(adq_frec)
record_time = 3 #s

save_png = True
save_csv = True

nSamples = int(record_time * adq_frec)
rgdSamples = (c_double*nSamples)()

if nSamples > 134217728.:
    print("Too many samples, lower the time or frequency")
    quit()


if adq_frec < 10000:
    print("Frequency too low, make it higher or change the mode")
    quit()


#print(DWF version
version = create_string_buffer(16)
dwf.FDwfGetVersion(version)
print("DWF Version: "+str(version.value))


#open device
print("Opening first device")
dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))


if hdwf.value == hdwfNone.value:
    szerr = create_string_buffer(512)
    dwf.FDwfGetLastErrorMsg(szerr)
    print(str(szerr.value))
    print("failed to open device")
    quit()

# Function to perform a single acquisition and read data
def acquire_data():
    
    cAvailable = c_int()
    cLost = c_int()
    cCorrupted = c_int()
    fLost = 0
    fCorrupted = 0
    
    cSamples = 0
    # Start the acquisition
    
    dwf.FDwfAnalogInConfigure(hdwf, c_int(0), c_int(1))
    
    # Wait for the acquisition to complete
    while cSamples < nSamples:
        dwf.FDwfAnalogInStatus(hdwf, c_int(1), byref(sts))
        if cSamples == 0 and (sts == DwfStateConfig or sts == DwfStatePrefill or sts == DwfStateArmed) :
            # Acquisition not yet started.
            continue

        dwf.FDwfAnalogInStatusRecord(hdwf, byref(cAvailable), byref(cLost), byref(cCorrupted))
    
        cSamples += cLost.value
        
        if cLost.value :
            fLost = 1
        if cCorrupted.value :
            fCorrupted = 1

        if cAvailable.value==0 :
            continue

        if cSamples+cAvailable.value > nSamples :
            cAvailable = c_int(nSamples-cSamples)
        
        
        dwf.FDwfAnalogInStatusData(hdwf, c_int(0), byref(rgdSamples, sizeof(c_double)*cSamples), cAvailable) # get channel 1 data
        #dwf.FDwfAnalogInStatusData(hdwf, c_int(1), byref(rgdSamples, sizeof(c_double)*cSamples), cAvailable) # get channel 2 data
        cSamples += cAvailable.value

    return rgdSamples, fLost, fCorrupted
    

dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0)) # 0 = the device will only be configured when FDwf###Configure is called

#set up acquisition
dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(0), c_int(1))
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(0), c_double(5))
dwf.FDwfAnalogInAcquisitionModeSet(hdwf, acqmodeRecord)
dwf.FDwfAnalogInFrequencySet(hdwf, hzAcq)
dwf.FDwfAnalogInRecordLengthSet(hdwf, c_double(nSamples/hzAcq.value)) # -1 infinite record length
dwf.FDwfAnalogInConfigure(hdwf, c_int(1), c_int(0))

#set up range channel by channel
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(0), c_double(5)) #1
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(1), c_double(5)) #2
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(2), c_double(5)) #3
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(3), c_double(5)) #4

#set up offset channel by channel
dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(0), c_double(0)) #1
dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(1), c_double(0)) #2
dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(2), c_double(0)) #3
dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(3), c_double(0)) #4

#wait at least 2 seconds for the offset to stabilize
time.sleep(2)

saving_directory = "Data/"

if __name__ == "__main__": 
    # creating multiprocessing Queue 
    q1 = multiprocessing.Queue(-1) 
    q2 = multiprocessing.Queue(-1) 
    acquisition_count = 0
    
    try:
        while True:
            start_time = time.time()

            print(f"Starting acquisition {acquisition_count}")
            # Perform an acquisition and write the data to the CSV file

            # Record the end time
            csv_name = saving_directory + "oscilloscope_data_" + str(acquisition_count) + ".csv"
            png_name = saving_directory + "oscilloscope_image_" + str(acquisition_count) + ".png"
    
        
            # creating new processes 
            p1 = multiprocessing.Process(target=sf.save, args=(csv_name, adq_frec, q1,)) 
            p2 = multiprocessing.Process(target=sf.save_plot, args=(png_name, q2,)) 

            data ,fLost, fCorrupted = acquire_data()
            py_data = list(data)
            if save_csv:
                q1.put(py_data)
                p1.start()
            if save_png:
                q2.put(py_data)
                p2.start()
            
            print(f"Acquisition {acquisition_count} completed")
            
            end_time = time.time()
            
            acquisition_count += 1
            print("iteration finished")
        
            # Calculate the time difference
            end_time = time.time()
            print("End time:", end_time - start_time)
        
        
    except KeyboardInterrupt:
        print("Acquisition stopped by user")
        dwf.FDwfAnalogOutReset(hdwf, c_int(0))
        dwf.FDwfDeviceCloseAll()