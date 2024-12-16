import socket


def connect_to_peer(peer_ip, peer_port):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Connect to the peer
        sock.connect((peer_ip, peer_port))
        print("Connection to peer established:", peer_ip, peer_port)
        # Perform further operations on the connected socket if needed
    except ConnectionRefusedError:
        print("Unable to connect to the peer:", peer_ip, peer_port)
    finally:
        # Close the socket
        sock.close()
        print("Connection closed")


# Example usage
peer_ip = "97.117.28.178"
peer_port = 80

connect_to_peer(peer_ip, peer_port)
