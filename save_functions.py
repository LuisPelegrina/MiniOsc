import time
import matplotlib.pyplot as plt
import numpy as np
import csv
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
            
            if len(data[1]) != len(data[1]): 
                print("RANGE ERROR IN SAVING")
                quit()
               
            if len(data[2]) != len(data[1]):
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
        insert_query = "INSERT INTO example_table (value, timestamp) VALUES (%s, %s);"
        for value, timestamp in zip(data[0], timestamp_list):
            dt_object = datetime.fromtimestamp(timestamp)
            formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S.%f')
            #print(formatted_time)
            #cur.execute(insert_query, (value, timestamp))

        cur.close()
        conn.close()
