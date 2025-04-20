import socket

HOST = '127.0.0.1'
PORT = 55432

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            while True:
                message = input("Enter message (or 'quit' to exit): ")
                if message.lower() == "quit":
                    #data = s.recv(1024)
                    #if not data:
                    #    break
                    #print(f"Last Received: {data.decode()}")
                    break
                s.sendall(message.encode())
                data = s.recv(1024)
                print(f"Received: {data.decode()}")

        except ConnectionRefusedError:
            print("Connection refused. Is the server running?")

if __name__ == "__main__":
    main()
