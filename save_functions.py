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

        
def save(file_name, q):
    if q.empty():
        print("Queue is empty!") 
    else:          
        print("Saving data")
        data = q.get()
        time_pre_get = time.time()
        with open(file_name, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Sample'] + ['Channel 1 [V]'])
            for i, value in enumerate(data):
                csvwriter.writerow([i, value])
            time_post_get = time.time()
            print("Writing time:",time_pre_get-time_post_get)