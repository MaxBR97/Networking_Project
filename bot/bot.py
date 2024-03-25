from  utils import network_utils
import random

def bot_behavior(tcp_socket):
    """
    Defines the bot's behavior during the game.
    """
    # Example bot behavior: send a random answer
    answer = random.choice(['y', 'n'])
    print(f"Bot automatically answering: {answer}")
    tcp_socket.sendall(answer.encode())

def main():
    server_ip = network_utils.listen_for_udp_broadcast()
    if server_ip:
        tcp_socket = network_utils.establish_tcp_connection(server_ip)
        if tcp_socket:
            try:
                # Initial handshake or sending bot's name
                tcp_socket.sendall("BotPlayer\n".encode())
                # Implement bot game interaction logic here
            finally:
                tcp_socket.close()
    else:
        print("No server offers detected.")

if __name__ == "__main__":
    main()
