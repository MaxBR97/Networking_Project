import socket
import select
import struct


# Constants
SERVER_UDP_PORT = 13117
BUFFER_SIZE = 1024

def find_available_port(start_port=5000, end_port=65535):
    for port in range(start_port, end_port + 1):
        try:
            # Try to create a socket on the given port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
            return port
        except OSError:
            continue  # Port is not available, try the next one
    return None  # No available port found in the given range

def get_local_ip():
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception as e:
        print("Error:", e)
        local_ip = None
    return local_ip

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
                magic_cookie, message_type, server_name_padded, tcp_port = struct.unpack('!IB32sH', message)
                server_name = server_name_padded.rstrip(b'\x00').decode('utf-8') 
                print(f"Received offer from server: {server_name} at address {server_address[0]} attempting to connect...")
                return server_address[0], tcp_port


def establish_tcp_connection(server_ip,dest_port):
    """
    Establish a TCP connection to the server using the provided IP.
    """
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        tcp_socket.connect((server_ip, dest_port))
        return tcp_socket
    except Exception as e:
        print(f"Could not connect to server at {server_ip}: {e}")
        return None
    

