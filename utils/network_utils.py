import socket
import select


# Constants
SERVER_UDP_PORT = 13117
TCP_PORT = 12345
BUFFER_SIZE = 1024

def listen_for_udp_broadcast():
    """
    Listen for UDP broadcasts from the server to discover game sessions.
    Allows multiple instances on the same machine by setting SO_REUSEPORT.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        # Allows the socket to be bound to an address that is already in use
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Further allows multiple instances of the application to receive UDP broadcasts on the same port      
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  #There was a requirement to use SO_REUSEPORT, though it's used only when WIN!=32. so we used this SO_BROADCAST to fix it.
        udp_socket.bind(('', SERVER_UDP_PORT))
        print("Listening for offer requests...")
        while True:
            ready_sockets, _, _ = select.select([udp_socket], [], [], 5)
            if ready_sockets:
                message, server_address = udp_socket.recvfrom(BUFFER_SIZE)
                print(f"Received offer from {server_address}, attempting to connect...")
                return server_address[0]

def establish_tcp_connection(server_ip):
    """
    Establish a TCP connection to the server using the provided IP.
    """
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        tcp_socket.connect((server_ip, TCP_PORT))
        print("Connected to the server.")
        return tcp_socket
    except Exception as e:
        print(f"Could not connect to server at {server_ip}: {e}")
        return None
