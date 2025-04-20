import socket
HOST = '127.0.0.1'  # localhost
PORT = 55432         # Port to listen on

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Listening on {HOST}:{PORT}")

        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"Received: {data.decode()}")
                conn.sendall(b"Server received: " + data) #echo data.
        print("Connection closed.")

if __name__ == "__main__":
    main()