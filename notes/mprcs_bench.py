import multiprocessing
import time
import pickle

def bencher(fn, operands):
    start_time = time.time()
    retrun = fn(*operands)
    end_time = time.time()
    deltarun = end_time - start_time
    return retrun, deltarun

def process_data(data):
    reg = 1
    for i in range(len(data)):
        # Simulate some work
        reg = (reg + data[i]) ** 0.3
        #del _   #apparently this can kill the python interpreter im guessing from garbage collection stuff haha
        #update: NEVER do this in a hot loop haha

def run_concurrent_tasks(data, data_tuple):
    #expect data, data_tuple
    data_process = multiprocessing.Process(target=process_data, args=(data,))
    tuple_process = multiprocessing.Process(target=process_data, args=(data_tuple,))

    data_process.start()
    tuple_process.start()

    # Wait for processes to finish
    data_process.join()
    tuple_process.join()

    return "Both concurrent tasks completed successfully."

def run_serial_tasks(data, data_tuple):
    #simulate list push and iterate
    serialized_data = pickle.dumps(data)
    deserialized_data = pickle.loads(serialized_data)
    process_data(deserialized_data)

    #simulate tuple push and iterate
    serialized_data = pickle.dumps(data_tuple)
    deserialized_data = pickle.loads(serialized_data)
    process_data(deserialized_data)
    return "Both serial tasks completed successfully."

if __name__ == "__main__":
    data_list = list(range(100000000))  #100000000 for 17s+28s
    data_tuple = tuple(data_list)
    _, dtime = bencher(run_concurrent_tasks,(data_list, data_tuple))
    print(_)
    print(f"concurrent op time:{dtime} secs")

    _, dtime = bencher(run_serial_tasks,(data_list, data_tuple))
    print(_)
    print(f"serial op time:{dtime} secs")