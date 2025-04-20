import pickle
import time
import sys

def benchmark(data):
    start_time = time.time()
    serialized_data = pickle.dumps(data)
    deserialized_data = pickle.loads(serialized_data)
    end_time = time.time()
    return end_time - start_time

data = list(range(10000000))
data_tuple = tuple(data)

list_time = benchmark(data)
tuple_time = benchmark(data_tuple)

print(f"List Serialization Time: {list_time:.6f} seconds")
print(f"Tuple Serialization Time: {tuple_time:.6f} seconds")
print(f"List Size: {sys.getsizeof(data)} bytes")
print(f"Tuple Size: {sys.getsizeof(data_tuple)} bytes")