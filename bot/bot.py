import socket
import select
import random

# Constants
SERVER_UDP_PORT = 13117
TCP_PORT = 12345
BUFFER_SIZE = 1024

def listen_for_udp_broadcast():
    """
    Listen for UDP broadcasts to discover the server for the game session.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(('', SERVER_UDP_PORT))

        print("Bot client started, listening for offer requests...")
        while True:
            ready_sockets, _, _ = select.select([udp_socket], [], [], 5)
            if ready_sockets:
                message, server_address = udp_socket.recvfrom(BUFFER_SIZE)
                print(f"Received offer from {server_address}, attempting to connect...")
                return server_address[0]

def connect_to_server(server_ip):
    """
    Establish a TCP connection to the server and automatically respond to trivia questions.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        try:
            tcp_socket.connect((server_ip, TCP_PORT))
            print("Connected to the server as a bot.")
            
            # Send bot's name or any initial handshake message required
            tcp_socket.sendall("BotPlayer\n".encode())

            # Bot game loop
            while True:
                server_message = tcp_socket.recv(BUFFER_SIZE).decode()
                if not server_message:
                    break  # Server closed the connection
                print(server_message)

                # If the message requires an answer, decide automatically
                if "Your answer:" in server_message:
                    # This is where you could make your bot smarter!
                    answer = random.choice(['True', 'False'])  # Randomly choose True or False
                    print(f"Bot automatically answering: {answer}")
                    tcp_socket.sendall(answer.encode())

        except Exception as e:
            print(f"Could not connect to server at {server_ip}: {e}")

if __name__ == "__main__":
    server_ip = listen_for_udp_broadcast()
    if server_ip:
        connect_to_server(server_ip)
    else:
        print("No server offers detected.")
