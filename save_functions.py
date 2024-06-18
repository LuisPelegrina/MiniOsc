import time
import matplotlib.pyplot as plt
import numpy as np
import csv
import multiprocessing 

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
