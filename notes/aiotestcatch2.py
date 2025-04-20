import asyncio
import socket
import concurrent.futures

HOST = '127.0.0.1'
SOCKET_RANGE_START = 55432  #Starting port for connections.
MAX_CONNECTIONS = 2048       #Maximum simultaneous connections.


# mapping func wooo
def setup_listening_range(start_port, num_connections):
    """
    Creates a specified number of listening sockets in sequence.

    Returns:
        A list of bound socket objects.
    """
    sockets = []
    l_range = []
    for i in range(num_connections):
        port = start_port + i
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('127.0.0.1', port))
            sock.listen(5)
            sockets.append(sock)
            l_range.append(port)
        except OSError as e:
            print(f"Error binding port {port}: {e}")
            pass
    return sockets, l_range


# async func wooo
async def connection_handler(connection, address, request_queue):
    """
    Handles a single client connection.

    Args:
        connection (socket): The active socket connection.
        address (tuple): The client's address (ip, port).
        request_queue (asyncio.Queue): Queue for handling messages.
    """
    BUFFER_SIZE = 1024
    while True:
        try:
            data = await asyncio.to_thread(connection.recv, BUFFER_SIZE) #Explicit threading context
            if not data:  # Connection closed
                print("client disconnected")
                return #exiting current loop
            await request_queue.put(data) #add message
        except ConnectionRefusedError:
            break #client quit without server cleanup
    print("no data left to recv")

#Helper function for sending messages.
async def write_to_connection(connection, message):
   await asyncio.to_thread(connection.sendall, message.encode())

#Handle a listening socket
async def listening_handler(sock, request_queue, listening_range):
        #print("Listening for connections") this prints more times than can be considered reasonable!
        while True:
            try:
                connection, address = await asyncio.to_thread(sock.accept)  #Accepts connections in background thread
                async def process_connection(connection, address, queue):
                    await connection_handler(connection, address, queue)
                    # We created the task, and passed queue into it
                    await asyncio.create_task(request_processor(connection, request_queue,listening_range))
                await asyncio.create_task(process_connection(connection, address, request_queue))
                #await process_connection(connection, address, request_queue) #this line!
            except ConnectionRefusedError:
                break


async def request_processor(connection, request_queue, listening_range):
    """
    Process the requests in the queue and update any internal state.

    Args:
        request_queue (asyncio.Queue): Queue containing raw received bytes.
        listening_sockets (list of sockets): 
    """
    BUFFER_SIZE = 2048
    while True:
        received_message = await request_queue.get()
        try:
           #print(f"Recieved msg: {received_message}") #raw bytes
            decoded_message = received_message.decode('utf-8')
            print(f"decoded message: {decoded_message}") #string message
            # Perform some action with the received data.
            # for example parse request type and parameters
            
            #echo response
            response = f"Server received message: {decoded_message}"
            #sample first handful of indices for socket announce query
            if decoded_message.startswith("🍀/api/socket_range", end=32):
                sep = ","
                response = sep.join(listening_range)

            # Convert response to bytes and send back to client
            #await write_to_connection(client, response)
            await connection.sendall(response)
        except Exception as e:
            print(f"An error occurred while processing the request: {e}")
            pass

async def main():
    listening_sockets = []  # List to store socket objects while they are bound
    listening_range = []    # list to store integer literals tracking bound sockets
    request_queue = asyncio.Queue()
    listening_sockets, listening_range = setup_listening_range(SOCKET_RANGE_START, MAX_CONNECTIONS)

    #Verify that the sockets have initialized before firing the task loop
    if len(listening_sockets) > 0:
        print(f"Successfully initialized {len(listening_sockets)} sockets!")
    else:
        print("socket initialization has failed.")
        return

    tasks = []

    print("Listening sockets setup")
    try:
      for sock in listening_sockets:
        async def start_handler(sock, queue, listening_range): #scope binding within our listener
            task = asyncio.create_task(listening_handler(sock, queue, listening_range))
            #move request_processor launch into listening_handler
            await listening_handler(sock, queue, listening_range)

        task = asyncio.create_task(start_handler(sock, request_queue, listening_range))  
        tasks.append(task)

        #asyncio.create_task(request_processor(request_queue, listening_range))  #give process return list for api stuff
      await asyncio.gather(*tasks) # Run until cancelled, or all connections gone.

    except KeyboardInterrupt:
       print("Stopping server")

    finally:
        # Clean up the sockets
        for s in listening_sockets:
            s.close()

if __name__ == "__main__":
    asyncio.run(main())