import sys
import os
from inputimeout import inputimeout
import random
import random
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)
from utils import network_utils
# Fill with names


def generate_random_number():
    return str(random.randint(1, 100))
def run_client(func,names_array):
    while True:
        server_ip, destination_tcp_port = network_utils.listen_for_udp_broadcast()
        if server_ip:
            try:
                tcp_socket = network_utils.establish_tcp_connection(server_ip, destination_tcp_port)
                # Choose from names_array randomly
                received_data = tcp_socket.recv(1024)
                received_text = received_data.decode('utf-8').strip()
                print(received_text)
                user_name = random.choice(names_array)#+generate_random_number()
                tcp_socket.send(f"{user_name}\n".encode('utf-8'))
                print(f"My team name: {user_name}")
                # Double threading: one for listening to the socket, another for user input
                received_data = tcp_socket.recv(1024)
                received_text = received_data.decode('utf-8').strip()
                print(received_text)
                while True:
                    received_data = tcp_socket.recv(1024)  # Adjust buffer size as needed
                    if not received_data:
                        break
                    received_text = received_data.decode('utf-8').strip()
                    print(received_text)
                    
                    # Check for game over conditions
                    if "game over" in received_text.lower():
                        break
                    #thread.daemon=True
                    if "round" not in received_text.lower() and "played by" not in received_text.lower():
                        func(tcp_socket)
                        
            except Exception as e:
                print(f"Error: {e}")
            finally:
                if tcp_socket:
                    tcp_socket.close()
        else:
            print("No server offers detected.")


