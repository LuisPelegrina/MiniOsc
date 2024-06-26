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

hdwf = c_int()
sts = c_byte()

version = create_string_buffer(16)
dwf.FDwfGetVersion(version)
print("DWF Version: "+str(version.value))

print("Opening first device")
dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))
# 2nd configuration for Analog Discovery with 16k analog-in buffer
#dwf.FDwfDeviceConfigOpen(c_int(-1), c_int(1), byref(hdwf)) 

if hdwf.value == hdwfNone.value:
    szError = create_string_buffer(512)
    dwf.FDwfGetLastErrorMsg(szError);
    print("failed to open device\n"+str(szError.value))
    quit()

dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0)) # 0 = the device will only be configured when FDwf###Configure is called

"""
CONFIG FOR SUNSETS:
2000 samples at 100e6 Hz rate

SWB_CH: 200 mV total, ~100 mV offset at 7kV
SWT_CH: 500 mV total, ~200 mV offset at 7kV
CH4: Trigger: 750 mV total,  NIM(500 mV negative pulse signal), 0 V offset
"""


save_csv = True

#To match sunset configuration we need 2k samples, to capture 20 mus window
nSamples = 2000
hzRate = 100e6
hzAcq = c_double(hzRate)
rgdSamples_channel1 = (c_double*nSamples)()
rgdSamples_channel2 = (c_double*nSamples)()
rgdSamples_channel3 = (c_double*nSamples)()
rgdSamples_channel4 = (c_double*nSamples)()

#set up acquisition
dwf.FDwfAnalogInFrequencySet(hdwf, hzAcq)
dwf.FDwfAnalogInBufferSizeSet(hdwf, c_int(nSamples))
dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(-1), c_int(1))
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(-1), c_double(5))
dwf.FDwfAnalogInChannelFilterSet(hdwf, c_int(-1), c_int(3))

#set up range channel by channel
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(0), c_double(0.2)) #1
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(1), c_double(5)) #2
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(2), c_double(5)) #3
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(3), c_double(1)) #4

#set up offset channel by channel
dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(0), c_double(-0.1)) #1
dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(1), c_double(0)) #2
dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(2), c_double(0)) #3
dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(3), c_double(0)) #4

#set up trigger
dwf.FDwfAnalogInTriggerAutoTimeoutSet(hdwf, c_double(0)) #disable auto trigger
dwf.FDwfAnalogInTriggerSourceSet(hdwf, trigsrcDetectorAnalogIn) #one of the analog in channels
dwf.FDwfAnalogInTriggerTypeSet(hdwf, trigtypeEdge)
dwf.FDwfAnalogInTriggerChannelSet(hdwf, c_int(3)) # Channel 4
dwf.FDwfAnalogInTriggerLevelSet(hdwf, c_double(-0.200)) # -200.0mV
dwf.FDwfAnalogInTriggerConditionSet(hdwf, DwfTriggerSlopeFall) 

# relative to middle of the buffer, with time base/2 T0 will be the first sample
#dwf.FDwfAnalogInTriggerPositionSet(hdwf, c_double(0.5*nSamples/hzRate)) 
dwf.FDwfAnalogInTriggerPositionSet(hdwf, c_double(0)) 

# wait at least 2 seconds with Analog Discovery for the offset to stabilize, before the first reading after device open or offset/range change
time.sleep(2)

print("Starting repeated acquisitions")
dwf.FDwfAnalogInConfigure(hdwf, c_int(1), c_int(1))


saving_directory = "/daq/scratch/FC_mini_osc/triggered_data/"
csv_name = saving_directory + "trigger_"
sec = c_uint(1)
tick = c_uint(1)
ticksec = c_uint(1)


if __name__ == "__main__": 
    # creating multiprocessing Queue 
    q1 = multiprocessing.Queue(-1) 
    
    try:
        while True:
            # Perform an acquisition and write the data to the CSV file
            # creating new processes 
            
            p1 = multiprocessing.Process(target=sf.save_trigger, args=(csv_name, hzRate, sec, tick, ticksec ,q1,)) 
            while True:
                dwf.FDwfAnalogInStatus(hdwf, c_int(1), byref(sts))
                if sts.value == DwfStateDone.value :
                    break
                time.sleep(0.001)

            dwf.FDwfAnalogInStatusData(hdwf, 0, rgdSamples_channel1, nSamples) # get channel 1 data
            dwf.FDwfAnalogInStatusData(hdwf, 1, rgdSamples_channel2, nSamples) # get channel 2 data
            dwf.FDwfAnalogInStatusData(hdwf, 2, rgdSamples_channel3, nSamples) # get channel 3 data
            dwf.FDwfAnalogInStatusData(hdwf, 3, rgdSamples_channel4, nSamples) # get channel 4 data

            dwf.FDwfAnalogInStatusTime(hdwf, byref(sec), byref(tick), byref(ticksec))   
            py_data = [list(rgdSamples_channel1), list(rgdSamples_channel2), list(rgdSamples_channel3), list(rgdSamples_channel4)] 
            q1.put(py_data)
            p1.start()
            

    except KeyboardInterrupt:
        print("Acquisition stopped by user")
        dwf.FDwfAnalogOutReset(hdwf, c_int(0))
        dwf.FDwfDeviceCloseAll()

