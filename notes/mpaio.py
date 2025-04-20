import multiprocessing
import pickle

#okay this one is annoying and seems to need a system of enclosure.
#

def task_gnosticator(data):
    reg = 1
    for i in range(len(data)):
        # Simulate some work
        reg = (reg + data[i]) ** 0.3
    return reg

def run_concurrent_tasks_pool(data, data_tuple, num_processes=(multiprocessing.cpu_count()-2)):
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(process_data, [(data,), (data_tuple,)])  #Use starmap for multiple arguments
        #results[0]:data return, results[1]:data_tuple return.
    return "Both concurrent tasks completed successfully."

async def tcp_transmembrane

if __name__ == "__main__":
    data_list = list(range(100000000))  #100000000 for 17s+28s
    data_tuple = tuple(data_list)
    _, dtime = bencher(run_concurrent_tasks_pool,(data_list, data_tuple))
    print(_)
    print(f"concurrent op time:{dtime} secs")

    _, dtime = bencher(run_serial_tasks,(data_list, data_tuple))
    print(_)
    print(f"serial op time:{dtime} secs")