#mprocessing
import asyncio
import socket
import multiprocessing
import time

HOST = '127.0.0.1'
START_PORT = 55432
MAX_CONNECTIONS = 2048
PORT_RANGE = 10

# Queues for communication
connection_queue = asyncio.Queue()
processing_queue = asyncio.Queue()
event_queue = asyncio.Queue()

async def worker_process(task_queue):
    #This is an example. Replace with your intensive processing logic
    while True:
        task = await task_queue.get()
        data = task
        # Simulate CPU-bound task
        time.sleep(0.1)  # Simulate processing time
        task_queue.task_done()

async def handle_connection(reader, writer):
    addr = writer.get_extra_info('peername')
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break

            #'logs' should be 'events' which should be 'asynchronous' 
            #this lets us decouple 'string operations' from a 'hot loop' that 'reads buffer'
            await event_queue.put(f"Received from {addr}: {data.decode()}")
            # Submit data to processing queue
            await processing_queue.put(data)

            #echo logic
            writer.write(b"Server received: " + data)
            await writer.drain()

    except ConnectionError:
        await event_queue.put(f"Connection lost from {addr}.")
    finally:
        await event_queue.put(f"Closing connection from {addr}.")
        writer.close()
        await writer.wait_closed()

async def eventparse(event_queue):
    rec = 0
    cerr = 0
    closed = 0
    while not event_queue.empty():
        ev = await event_queue.get()
        rectruthy = "received" in ev.lower()
        cerrtruthy = "connection lost" in ev.lower()
        closedtruthy = "closing" in ev.lower()
        rec += 1 * rectruthy
        cerr += 1 * cerrtruthy
        closed += 1 * closedtruthy
        event_queue.task_done()

    #old = (old[0]+rec, old[1]+cerr, old[2]+closed)
    #retstring = f"rec:{rec}/{old[0]}, errors:{cerr}/{old[1]}, closed:{closed}/{old[2]}"

    return (rec, cerr, closed) #avoid infinite loop

async def start_server_on_port(fn, host, port):
    try:
        server = await asyncio.start_server(fn, host, port)

        #might be unprintable for kiloports
        print(f"Server listening on {host}:{port}")
        async with server:
            await server.serve_forever()
    except Exception as e:
        print(f"Error starting server on port {port}: {e}")

async def main():

    loop = asyncio.get_running_loop()

    tasks = [asyncio.create_task(start_server_on_port(handle_connection, HOST, port))
             for port in range(START_PORT, START_PORT + PORT_RANGE+1)]

    #so this is how you ensemble plural serve_forevers.
    await asyncio.gather(*tasks)

    # this might only ever print after the server beefs it!
    ret = await eventparse(event_queue)
    print(ret)

if __name__ == "__main__":
    asyncio.run(main())