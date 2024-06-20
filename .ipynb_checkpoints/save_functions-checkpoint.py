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

def save_plot(file_name,q):
    if q.empty():
        print("Queue is empty!") 
    else:          
        print("Plotting")
        data = q.get()
        plt.plot(np.fromiter(data, dtype = float))
        plt.savefig(file_name)

        
def save(file_name, freq, q):
    if q.empty():
        print("Queue is empty!") 
    else:          
        print("Saving data")
        data = q.get()
        time_pre_get = time.time()
        with open(file_name, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Time (s)'] + ['Channel 1 [V]'])
            for i, value in enumerate(data):
                csvwriter.writerow([i*1./freq, value])
            time_post_get = time.time()
            print("Writing time:",time_pre_get-time_post_get)

def save_multi(file_name, freq, q):
    if q.empty():
        print("Queue is empty!") 
    else:          
        print("Saving data")
        data = q.get()
        time_pre_get = time.time()
        with open(file_name, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Time (s)'] + ['Channel 1 [V]'] + ['Channel 2 [V]'] + ['Channel 3 [V]']+ ['Channel 4 [V]'])

            if len(data[0]) != len(data[1]):
                print("RANGE ERROR IN SAVING")
                quit()
            
            if len(data[1]) != len(data[2]): 
                print("RANGE ERROR IN SAVING")
                quit()
               
            if len(data[1]) != len(data[3]):
                print("RANGE ERROR IN SAVING")
                quit()
            
            for i in range(len(data[0])):
                csvwriter.writerow([i*1./freq, data[0][i], data[1][i], data[2][i], data[3][i]])   
                
            time_post_get = time.time()
            print("Writing time:",time_pre_get-time_post_get)

def save_trigger(file_name, freq, sec, tick, ticksec ,q):
    if q.empty():
        print("Queue is empty!") 
    else:          
        data = q.get()
        
        s = time.localtime(sec.value)
        ns = 1e9/ticksec.value*tick.value
        ms = math.floor(ns/1e6)
        ns -= ms*1e6
        us = math.floor(ns/1e3)
        ns -= us*1e3
        ns = math.floor(ns)
        print(time.strftime("%Y-%m-%d-%H-%M-%S", s) +"-"+str(ms).zfill(3)+"-"+str(us).zfill(3)+"-"+str(ns).zfill(3))
        file_name = file_name + str(time.strftime("%Y-%m-%d-%H-%M-%S", s) +"-"+str(ms).zfill(3)+"-"+str(us).zfill(3)+"-"+str(ns).zfill(3)) + ".csv"
    
        with open(file_name, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Time (s)'] + ['Channel 1 [V]'] + ['Channel 2 [V]'] + ['Channel 3 [V]']+ ['Channel 4 [V]'])

            if len(data[0]) != len(data[1]):
                print("RANGE ERROR IN SAVING")
                quit()
            
            if len(data[1]) != len(data[2]): 
                print("RANGE ERROR IN SAVING")
                quit()
                
            if len(data[1]) != len(data[3]): 
                print("RANGE ERROR IN SAVING")
                quit()
                
            for i in range(len(data[0])):
                csvwriter.writerow([i*1./freq, data[0][i], data[1][i], data[2][i], data[3][i]])   
              
    