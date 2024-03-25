import sys
import os
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)
from utils import network_utils
import random
import socket

def bot_behavior(tcp_socket: socket):
    """
    Defines the bot's behavior during the game.
    """
    # Example bot behavior: send a random answer
    received_data = tcp_socket.recv(1024)  # Adjust buffer size as needed
    received_text = received_data.decode('utf-8')
    print(f'bot recieved {received_text}')
    answer = random.choice(['y', 'n'])
    print(f"Bot automatically answering: {answer}")
    tcp_socket.send(answer.encode())

def main():
    server_ip = network_utils.listen_for_udp_broadcast(1)
    if server_ip:
        tcp_socket = network_utils.establish_tcp_connection(server_ip)
        if tcp_socket:
            try:
                while True:
                # Initial handshake or sending bot's name
                    bot_behavior(tcp_socket)
                # Implement bot game interaction logic here
            except Exception as e:
                print(e)
            finally:
                tcp_socket.close()
    else:
        print("No server offers detected.")

if __name__ == "__main__":
    main()
