from utils import network_utils
# import sys

def main():
    server_ip = network_utils.listen_for_udp_broadcast()
    if server_ip:
        tcp_socket = network_utils.establish_tcp_connection(server_ip)
        if tcp_socket:
            try:
                while True:
                    user_input = input("Enter something: ")
                    if user_input !=0 or user_input !=1:
                        print("insert valid input")
                    else:
                        data_to_send = user_input.encode('utf-8')
                        tcp_socket.send(data_to_send)
            finally:
                tcp_socket.close()
    else:
        print("No server offers detected.")

if __name__ == "__main__":
    main()
