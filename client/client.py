import sys
import os
import time
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)
from utils import network_utils
#TODO: fill with names
names_array=[]

def main():
    #TODO: change to double threaded so one lsiten to socket and other listen to user input
    #TODO: extract common behavior of client and bot to other class the only different is that client get answers from input 
    while True:
        server_ip = network_utils.listen_for_udp_broadcast()
        if server_ip:
            try:
                tcp_socket = network_utils.establish_tcp_connection(server_ip)
                received_data = tcp_socket.recv(1024)  # Adjust buffer size as needed
                received_text = received_data.decode('utf-8')
                #TODO: choose from names_array
                user_input = "Idan"
                data_to_send = user_input.encode('utf-8')
                tcp_socket.send(data_to_send+b'\n')
                received_data = tcp_socket.recv(1024)  # Adjust buffer size as needed
                received_text = received_data.decode('utf-8')
                print(received_text)
                if tcp_socket:    
                        while True:
                            received_data = tcp_socket.recv(1024)  # Adjust buffer size as needed
                            received_text = received_data.decode('utf-8')
                            received_text = received_text.strip()
                            #TODO: remove if below and keep running and print server messages until get "Game over!..."
                            if received_text=='you are out of the game, you have lost' or received_text=='you won!':
                                print(received_text)
                                time.sleep(2)
                                break
                            print(received_text)
                            user_input = input("true(y) or false (n): ")
                            if user_input !='y' and user_input !='n':
                                print("insert valid input")
                            else:
                                data_to_send = user_input.encode('utf-8')
                                tcp_socket.send(data_to_send)
            except Exception as e:
                    print(e)
            finally:
                    if tcp_socket:
                        tcp_socket.close()
        else:
            print("No server offers detected.")

if __name__ == "__main__":
    main()
