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
import configparser
import psycopg2
from datetime import datetime

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

 def read_db_config(filename, section):
    parser = configparser.ConfigParser()
    parser.read(filename)

    db_config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db_config[param[0]] = param[1]
    else:
        raise Exception(f"Section {section} not found in the {filename} file")

    return db_config

def generate_timestamps(start_time, freq, length):
    increment = float(1/freq)
    timestamps = [start_time]

    for _ in range(1, length):
        next_timestamp = timestamps[-1] + increment
        timestamps.append(next_timestamp)

    return timestamps

def write_db(start_time, freq, down_spl, q):
    if q.empty():
        print("Queue is empty!")

    else:
        conn_params = read_db_config('/home/nfs/sbnddcs/configs/archiver/postgreSQL_db.ini', 'writer')
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        cur.execute("set search_path to dcs_prd;")
        cur.execute("SELECT * FROM sample WHERE channel_id = 17492;")
        data = q.get()
        if len(data[0]) != len(data[1]):
            print("RANGE ERROR IN SAVING")
            quit()
        if len(data[1]) != len(data[1]):
            print("RANGE ERROR IN SAVING")
            quit()
        if len(data[2]) != len(data[1]):
            print("RANGE ERROR IN SAVING")
            quit()
            
        list_len = len(data[0])
        timestamp_list = generate_timestamps(start_time, freq, list_len)

        # Define the insert SQL query
        insert_query = "INSERT INTO sample (channel_id,float_val,smpl_time,nanosecs,severity_id,status_id) VALUES (%s, %s, %s, %s, %s, %s);"
        ch1_channel_id = 17492
        ch2_channel_id = 17493
        ch3_channel_id = 17494
        ch4_channel_id = 17495

        for i in range(0, len(data[0]), down_spl):
            ch1_val = data[0][i]
            ch2_val = data[1][i]
            ch3_val = data[2][i]
            #ch4_val = data[3][i]

            timestamp = timestamp_list[i]
            decimal_part = str(timestamp).split('.')[1]
            dt_object = datetime.fromtimestamp(timestamp)
            formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S.%f')

            ch1_data = (ch1_channel_id, ch1_val, formatted_time, int(decimal_part), 5, 4);
            ch2_data = (ch2_channel_id, ch2_val, formatted_time, int(decimal_part), 5, 4);
            ch3_data = (ch3_channel_id, ch3_val, formatted_time, int(decimal_part), 5, 4);
            cur.execute(insert_query, ch1_data)
            cur.execute(insert_query, ch2_data)
            cur.execute(insert_query, ch3_data)
            conn.commit()
        
        cur.close()
        conn.close()
        
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
              
    