import socket


def start_server(host, port):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind the socket to the host and port
    sock.bind((host, port))
    # Listen for incoming connections
    sock.listen(1)
    print("Server started. Listening for connections...")
    # Accept incoming connections
    while True:
        connection, address = sock.accept()
        print("Connected by:", address)
        # Perform further operations on the connection if needed
        # For example, you can receive data from the client:
        # data = connection.recv(1024)
        # And send a response back:
        # connection.sendall(b"Hello from the server!")
        # Finally, close the connection
        connection.close()


# Example usage
host = "127.0.0.1"
port = 80

start_server(host, port)
