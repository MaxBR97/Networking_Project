import sys
import os
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)
from utils import network_utils


def main():
    server_ip = network_utils.listen_for_udp_broadcast()
    if server_ip:
        tcp_socket = network_utils.establish_tcp_connection(server_ip)
        if tcp_socket:
            try:
                while True:
                    received_data = tcp_socket.recv(1024)  # Adjust buffer size as needed
                    received_text = received_data.decode('utf-8')
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
                tcp_socket.close()
    else:
        print("No server offers detected.")

if __name__ == "__main__":
    main()
