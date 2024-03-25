import socket
import threading
import time
import random

# Constants
UDP_PORT = 13117
TCP_PORT = 12345
BROADCAST_INTERVAL = 1  # Seconds between broadcasts
WAITING_TIME_LEFT = 10
PARTICIPANTS = [] # element: [client_socket, address, still in game? (boolean)]
MAX_CONNECTIONS = 8  # Maximum number of simultaneous client connections
HOSTNAME = "172.20.10.10"
QUESTIONS = [["Question 1: the answer is Y", True], ["Question 2: the answer is N", False]]
CURRENT_QUESTION = 0
finishedRecruiting = False
SynchronizeRound= True 
def set_finished_recruiting(bool):
    global finishedRecruiting
    finishedRecruiting = bool
def broadcast_udp():
    """
    Broadcast UDP offer messages to clients periodically.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_socket.bind((HOSTNAME, UDP_PORT))
        global WAITING_TIME_LEFT
        message = f"""Server here! Connect to me for trivia fun!
                    HOSTNAME: {HOSTNAME}
                    TCP PORT: {TCP_PORT}"""
        keepWaiting = True
        while keepWaiting:
            try:
                udp_socket.sendto(message.encode(), ('<broadcast>', UDP_PORT))
                print(f"Broadcast message sent! (time left: {WAITING_TIME_LEFT})")
                time.sleep(BROADCAST_INTERVAL)
                WAITING_TIME_LEFT  = WAITING_TIME_LEFT - 1
                keepWaiting = False if WAITING_TIME_LEFT <= 0 else True
            except Exception as e:
                print(f"Error broadcasting: {e}")
        finishedRecruiting = True

def handle_client(client_socket, address):
    """
    Handle a connected client.
    """
    
    try:
        print(f"Connection from {address} has been established.")
        client_socket.send(bytes("Welcome to the trivia game!", "utf-8"))
        while not gamePhase:
            time.sleep(100)
        while gamePhase:
            SynchronizeRound.wait()
            if isStillParticipating(client_socket):
                startTime = time.thread_time_ns
                try:
                    client_socket.send(bytes(CURRENT_QUESTION[0], "utf-8"))
                    client_socket.settimeout(10 - time.thread_time_ns + startTime)
                    response = client_socket.recv(1024).decode("utf-8")
                    registerAnswer(client_socket, response)
                    print(f"Response from {address}: {response}")
                except socket.timeout:
                    print(f"Timeout occurred while waiting for response from {address}")
                    break  # Exit the loop if a timeout occurs
            else:
                client_socket.send(bytes("you are out of the game, you have lost", "utf-8"))
            
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
        tcp_socket.bind((HOSTNAME, TCP_PORT))
        tcp_socket.listen(MAX_CONNECTIONS)
        print(f"TCP server listening on port {TCP_PORT}...")
        
        while not finishedRecruiting:
            client_socket, address = tcp_socket.accept()
            WAITING_TIME_LEFT = 10
            PARTICIPANTS.append([client_socket, address, True])
            client_thread = threading.Thread(target=handle_client, args=(client_socket, address))
            client_thread.start()

if __name__ == "__main__":
    while True:
        udp_thread = threading.Thread(target=broadcast_udp)
        udp_thread.start()

        tcp_server_thread = threading.Thread(target=start_tcp_server)
        tcp_server_thread.start()
        udp_thread.join()

        timer = threading.Timer(0.2, set_finished_recruiting,args=(True,))
        timer.start()

        tcp_server_thread.join()
        gamePhase = True
        time.sleep(105)
        #game phase
        while getWinner() == None:
            CURRENT_QUESTION = pick_random_question()
            SynchronizeRound.notify_all()
            time.sleep(10050)
            endRound()

        
        finishGame()

    
    

#restart variables to finish the game appropriately, 
#and be ready for another game
def finishGame():
    return 0

#   return true or false, if client_socket is still participating,
#   meanning he didnt answer wrong so far.
def isStillParticipating(client_socket):
    return 0

#If there is a winner , return him (ip address or something),
# If no winner, return None
def getWinner():
    return None

#Calculate round results, expell players who answered wrong.
def endRound():
    return 0
# register the answer for a question given by the given client in a queue,
# which hold the order in which the answers were registered
def registerAnswer(client_socket, question ,answer):
    return 0

def pick_random_question():
    return random.choice(QUESTIONS)

# Example usage:
random_question = pick_random_question(QUESTIONS)
