"""
   DWF Python Example
   Author:  Digilent, Inc.
   Revision:  2022-03-08

   Requires:                       
       Python 2.7, 3
"""

from ctypes import *
from dwfconstants import *
import math
import time
import sys
import matplotlib.pyplot as plt
import numpy


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

#To match sunset configuration we need 2k samples, to capture 20 mus window
cSamples = 2000
hzRate = 100e6
rgdSamples = (c_double*cSamples)()

#set up acquisition
dwf.FDwfAnalogInFrequencySet(hdwf, hzAcq)
dwf.FDwfAnalogInBufferSizeSet(hdwf, c_int(nSamples))
dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(-1), c_int(1))
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(-1), c_double(5))
dwf.FDwfAnalogInChannelFilterSet(hdwf, c_int(-1), c_int(3))


"""
CONFIG FOR SUNSETS:
SWB_CH: 200 mV total, ~100 mV offset at 7kV
SWT_CH: 500 mV total, ~200 mV offset at 7kV
CH4: Trigger: 750 mV total,  NIM(500 mV negative pulse signal), 0 V offset
"""

#set up range channel by channel
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(0), c_double(0.2)) #1
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(1), c_double(0.2)) #2
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(2), c_double(0.4)) #3
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(3), c_double(0.4)) #4

#set up offset channel by channel
dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(0), c_double(-1)) #1
dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(1), c_double(0.5)) #2
dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(2), c_double(0)) #3
dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(3), c_double(0)) #4

#set up trigger
dwf.FDwfAnalogInTriggerAutoTimeoutSet(hdwf, c_double(0)) #disable auto trigger
dwf.FDwfAnalogInTriggerSourceSet(hdwf, trigsrcDetectorAnalogIn) #one of the analog in channels
dwf.FDwfAnalogInTriggerTypeSet(hdwf, trigtypeEdge)
dwf.FDwfAnalogInTriggerChannelSet(hdwf, c_int(3)) # Channel 4
dwf.FDwfAnalogInTriggerLevelSet(hdwf, c_double(-100.0)) # -100.0mV
dwf.FDwfAnalogInTriggerConditionSet(hdwf, DwfTriggerSlopeFall) 

# relative to middle of the buffer, with time base/2 T0 will be the first sample
dwf.FDwfAnalogInTriggerPositionSet(hdwf, c_double(0.5*cSamples/hzRate)) 

dwf.FDwfAnalogInConfigure(hdwf, c_int(1), c_int(0))
# wait at least 2 seconds with Analog Discovery for the offset to stabilize, before the first reading after device open or offset/range change
time.sleep(2)

print("Starting repeated acquisitions")
dwf.FDwfAnalogInConfigure(hdwf, c_int(0), c_int(1))


saving_directory = "/daq/scratch/FC_mini_osc/triggered_data/"

for iTrigger in range(10):
    # new acquisition is started automatically after done state 

    while True:
        dwf.FDwfAnalogInStatus(hdwf, c_int(1), byref(sts))
        if sts.value == DwfStateDone.value :
            break
        time.sleep(0.001)
    
    dwf.FDwfAnalogInStatusData(hdwf, 0, rgdSamples, cSamples) # get channel 1 data
    #dwf.FDwfAnalogInStatusData(hdwf, 1, rgdSamples, cSamples) # get channel 2 data
    
    dc = sum(rgdSamples)/len(rgdSamples)
    print("Acquisition #"+str(iTrigger)+" average: "+str(dc)+"V")
    
    sec = c_uint()
    tick = c_uint()
    ticksec = c_uint()
    
    # acquisition software time for Analog Discovery and T0 with 8-10ns precision for ADP3X50
    dwf.FDwfAnalogInStatusTime(hdwf, byref(sec), byref(tick), byref(ticksec))
    s = time.localtime(sec.value)
    ns = 1e9/ticksec.value*tick.value
    ms = math.floor(ns/1e6)
    ns -= ms*1e6
    us = math.floor(ns/1e3)
    ns -= us*1e3
    ns = math.floor(ns)
    print(time.strftime("%Y-%m-%d %H:%M:%S", s)+"."+str(ms).zfill(3)+"."+str(us).zfill(3)+"."+str(ns).zfill(3))
    
dwf.FDwfAnalogOutConfigure(hdwf, c_int(0), c_int(0))
dwf.FDwfDeviceCloseAll()

plt.plot(numpy.fromiter(rgdSamples, dtype = numpy.float))
plt.show()


