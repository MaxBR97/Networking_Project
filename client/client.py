import sys
import os
import time
import threading
import random
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)
from utils import network_utils

global lock

# Fill with names
names_array = ["Roee", "Maxim", "Idan", "Yossi", "Gal"]

def handle_user_input(tcp_socket):
    
    my_name = input("Please")
    while True:
        user_input = input("true (y) or false (n): ")
        if user_input in ['y', 'n']:
            data_to_send = user_input.encode('utf-8')
            tcp_socket.send(data_to_send)
        else:
            print("Please enter a valid input ('y' or 'n').")

def main():
    while True:
        server_ip, destination_tcp_port = network_utils.listen_for_udp_broadcast()
        if server_ip:
            try:
                tcp_socket = network_utils.establish_tcp_connection(server_ip, destination_tcp_port)
                # Choose from names_array randomly
                user_name = random.choice(names_array)
                tcp_socket.send(f"{user_name}\n".encode('utf-8'))

                # Double threading: one for listening to the socket, another for user input
                threading.Thread(target=handle_user_input, args=(tcp_socket,), daemon=True).start()

                while True:
                    received_data = tcp_socket.recv(1024)  # Adjust buffer size as needed
                    if not received_data:
                        break
                    received_text = received_data.decode('utf-8').strip()
                    print(received_text)
                    # Check for game over conditions
                    if "game over" in received_text.lower():
                        break


            except Exception as e:
                print(f"Error: {e}")
            finally:
                if tcp_socket:
                    tcp_socket.close()
        else:
            print("No server offers detected.")

if __name__ == "__main__":
    main()
