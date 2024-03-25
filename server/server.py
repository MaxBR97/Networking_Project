import socket
import threading
import time

# Constants
UDP_PORT = 13117
TCP_PORT = 12345
BROADCAST_INTERVAL = 10  # Seconds between broadcasts
MAX_CONNECTIONS = 5  # Maximum number of simultaneous client connections

def broadcast_udp():
    """
    Broadcast UDP offer messages to clients periodically.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = "Server here! Connect to me for trivia fun!"
        while True:
            try:
                udp_socket.sendto(message.encode(), ('<broadcast>', UDP_PORT))
                print("Broadcast message sent!")
                time.sleep(BROADCAST_INTERVAL)
            except Exception as e:
                print(f"Error broadcasting: {e}")

def handle_client(client_socket, address):
    """
    Handle a connected client.
    """
    try:
        print(f"Connection from {address} has been established.")
        client_socket.send(bytes("Welcome to the trivia game!", "utf-8"))
        # Here, you would add the logic to interact with the client during the game.
    except Exception as e:
        print(f"Error handling client {address}: {e}")
    finally:
        client_socket.close()

def start_tcp_server():
    """
    Start the TCP server to accept client connections.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.bind(('', TCP_PORT))
        tcp_socket.listen(MAX_CONNECTIONS)
        print(f"TCP server listening on port {TCP_PORT}...")
        
        while True:
            client_socket, address = tcp_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket, address))
            client_thread.start()

if __name__ == "__main__":
    udp_thread = threading.Thread(target=broadcast_udp)
    udp_thread.start()

    start_tcp_server()
