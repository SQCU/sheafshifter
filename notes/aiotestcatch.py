import asyncio
import socket
HOST = '127.0.0.1'  # localhost
PORT = 55432         # Port to listen on

eventstrings = []
old = (0,0,0)

async def handle_connection(reader, writer):
    addr = writer.get_extra_info('peername')
    #print(f"Connection from {addr}")
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break

            eventstrings.append(f"Received from {addr}: {data.decode()}")  #Briefly report source

            # simulate latency, with increasing randomness.
            await asyncio.sleep(0.2 + (hash(data) % 0.3))  #Add some jitter/delay

            writer.write(b"Server received: " + data)
            await writer.drain()

            if "eventparse" in data.decode():
                retstr = await eventparse(eventstrings, old)
                writer.write(retstr.encode())

            if "syskill" in data.decode():
                eventstrings.append(f"SYSKILL:Closing connection from {addr}.")
                writer.close()

    except ConnectionError:
        eventstrings.append(f"Connection lost from {addr}.")
    finally:
        eventstrings.append(f"Closing connection from {addr}.")
        writer.close()
        await writer.wait_closed()

async def eventparse(eventstrings, old):
    rec = 0
    cerr = 0
    closed = 0
    await asyncio.sleep(0.9 + (hash(old) % 0.3)) #shred list intermittently
    for ev in eventstrings:
        rectruthy = "received" in ev.lower()
        cerrtruthy = "connection lost" in ev.lower()
        closedtruthy = "closing" in ev.lower()
        rec+= 1*rectruthy
        cerr+= 1*cerrtruthy
        closed+= 1*closedtruthy
    old = (old[0]+rec, old[1]+cerr, old[2]+closed)
    eventstrings.clear()
    retstring = f"rec:{rec}/{old[0]}, errors:{cerr}/{old[1]}, closed:{closed}/{old[2]}"
    print(retstring)
    return retstring

async def main():
    eventstrings = []
    old = (0,0,0)

    loop = asyncio.get_running_loop()

    server = await asyncio.start_server(
        handle_connection, HOST, PORT
    )
    print(f"Listening on {HOST}:{PORT}")

    async with server:  #When used in an async with statement, the Server is closed when the with statement is completed:
        await server.serve_forever()

    await eventparse(eventstrings, old)

if __name__ == "__main__":
    asyncio.run(main())
