from utils import network_utils
# import sys

def main():
    server_ip = network_utils.listen_for_udp_broadcast()
    if server_ip:
        tcp_socket = network_utils.establish_tcp_connection(server_ip)
        if tcp_socket:
            try:
                # Send player's name or any initial handshake required
                tcp_socket.sendall("PlayerName\n".encode())
                # Handle game interaction here
            finally:
                tcp_socket.close()
    else:
        print("No server offers detected.")

if __name__ == "__main__":
    main()
