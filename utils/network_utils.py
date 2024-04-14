import socket
import select
import re
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
    # Create a socket object
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to any address; this will return the local IP address
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    except Exception as e:
        print("Error:", e)
        local_ip = None
    finally:
        s.close()
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
                #print(f"Received offer from {server_address}.\n Message: {bytes_to_string(message)}")
                return server_address[0], tcp_port


def bytes_to_string(message):
    if isinstance(message, bytes):
        print(message)
        message = message.decode('utf-8')
    return message


def extract_tcp_port(string_with_port):
    # Ensure string_with_port is decoded to a string
    if isinstance(string_with_port, bytes):
        string_with_port = string_with_port.decode('utf-8')

    # Define a regular expression pattern to match the substring "TCP PORT: {TCP_PORT}"
    pattern = r"TCP PORT: (\d+)"

    # Use re.search to find the first match of the pattern in the string
    match = re.search(pattern, string_with_port)

    if match:
        # Extract the port number from the matched group
        port_str = match.group(1)

        # Convert the port number string to an integer
        try:
            port_number = int(port_str)
            return port_number
        except ValueError:
            print("Error: Invalid port number format")
            return None
    else:
        print("Error: Port number not found in the string")
        return None


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
    

