"""
   DWF Python Example
   Author:  Digilent, Inc.
   Revision:  2018-07-19

   Requires:                       
       Python 2.7, 3
"""
#load things
from ctypes import *
from dwfconstants import *
import math
import time
import sys
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

adq_frec = 100 # Hz
down_spl = 10 # Save 1/down_spl of data to slow control DB
hzAcq = c_double(adq_frec)
record_time = 10 # sec

save_csv = True
write_db = False

nSamples = int(record_time * adq_frec)
rgdSamples_channel1 = (c_double*nSamples)()
rgdSamples_channel2 = (c_double*nSamples)()
rgdSamples_channel3 = (c_double*nSamples)()
rgdSamples_channel4 = (c_double*nSamples)()

if nSamples > 128000000.:
    print("Number of samples exceed oscilloscope buffer, lower the time, frequency or use Record function")
    quit()

version = create_string_buffer(16)
dwf.FDwfGetVersion(version)
print("DWF Version: "+str(version.value))

dwf.FDwfParamSet(DwfParamOnClose, c_int(0)) # 0 = run, 1 = stop, 2 = shutdown

#print(DWF version
version = create_string_buffer(16)
dwf.FDwfGetVersion(version)
print("DWF Version: "+str(version.value))


#open device
print("Opening first device")
#dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

dwf.FDwfDeviceOpenEx("ip:10.226.35.165\user:digilent\pass:digilent", byref(hdwf))


if hdwf.value == hdwfNone.value:
    szerr = create_string_buffer(512)
    dwf.FDwfGetLastErrorMsg(szerr)
    print(str(szerr.value))
    print("failed to open device")
    quit()

print("Acquisition stopped by user")
dwf.FDwfAnalogOutReset(hdwf, c_int(0))
dwf.FDwfDeviceCloseAll()
        
        

