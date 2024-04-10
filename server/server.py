import socket
import threading
import os
import sys
import time
import random
from queue import Queue
from question import questions
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)
from utils.network_utils import get_local_ip

# Constants
UDP_PORT = 13117
# TODO: make those dynamic and remove Constants maybe use find_available_port function from above
TCP_PORT = find_available_port()
HOSTNAME = get_local_ip()
BROADCAST_INTERVAL = 1  # Seconds between broadcasts
MAX_CONNECTIONS = 8  # Maximum number of simultaneous client connections




# Use a lock for thread-safe operations on shared resources




class Server():
    def __init__(self):
        self.udp_port=13117
        self.waiting_time_left=10
        self.answer_queue=Queue()# To store answers in the order they're received
        self.synchronize_round=threading.Condition()
        self.game_phase=False
        self.current_question=0
        self.finished_recruiting = False
        self.finished_recruiting_condition=threading.Condition()
        self.game_started_condition = threading.Condition()
        self.participations_lock = threading.Lock()
        self.participants = [] # element: [client_socket, address, still in game? (boolean)]
        self.queue_lock=threading.Lock()
        self.answers_dict={}
        self.answers_lock=threading.Lock()
        #TODO: Bonus add to those so we can have statictics and print/print and send those at the end of every game
        self.total_questions={}
        self.corrected_questions={}
        self.total_questions_lock=threading.Lock()
        self.corrected_questions_lock=threading.Lock()
    def finishGame(self):
        """
        Restart variables to finish the game appropriately and be ready for another game.
        Resets the game state, clears participants, and prepares for a new game.
        """
        self.participations_lock.acquire()
        self.participants=[]
        self.participations_lock.release()
        self.game_phase = False
        self.waiting_time_left = 10  # Reset waiting time
        self.current_question = 0  # Reset to the first question
        self.finished_recruiting=False
        with self.synchronize_round:
            self.synchronize_round.notify_all()

    def isStillParticipating(self, team_name:str):
        """
        Return true if client_socket is still participating, meaning they didn't answer wrong so far.
        """
        self.participations_lock.acquire()
        for participant in self.participants:
            if participant[1]==team_name:
                self.participations_lock.release()     
                print(participant[3])    
                return participant[3]  # The boolean flag for participation
        self.participations_lock.release()
        print(False)
        return False

    def endRound(self):
        """
        Calculate round results, expel players who answered wrong.
        """
        #TODO: change this function to check true/false in answers dict as answers will be checked in handle_client function
        #TODO: if all false dont do anything else change participant[3] = False only
        self.queue_lock.acquire()
        while not self.answer_queue.empty():
            team_name, answer = self.answer_queue.get()
            correct_answer = self.current_question[1]
            if (answer == 'y' and not correct_answer) or (answer == 'n' and correct_answer):
                print(f"{team_name} is incorrect.")
                # Mark the participant as not participating anymore
                self.participations_lock.acquire()
                for participant in self.participants:
                    if participant[1]==team_name:
                        participant[3] = False  # Update participation status
                        participant[0].send(bytes("you are out of the game, you have lost", "utf-8"))
                        participant[0].close()
                        break
                self.participations_lock.release()
            else:
                print(f"{team_name} is correct!")
        self.queue_lock.release()

    def endRound(self):
        """
        Calculate round results, expel players who answered wrong.
        """
        with self.queue_lock:
            while not self.answer_queue.empty():
                team_name, answer = self.answer_queue.get()
                correct_answer = self.current_question[1]
                if (answer == 'y' and not correct_answer) or (answer == 'n' and correct_answer):
                    # Update to use dictionary
                    self.answers_dict[team_name] = False
                    # Mark the participant as not participating anymore
                    with self.participations_lock:
                        for participant in self.participants:
                            if participant[1] == team_name:
                                participant[3] = False  # Update participation status
                                participant[0].send(bytes("you are out of the game, you have lost", "utf-8"))
                                participant[0].close()
                                break
                else:
                    self.answers_dict[team_name] = True
                    print(f"{team_name} is correct!")

    def registerAnswer(self,client_socket, answer):
        #TODO: change this function to insert to answers_dict instead of queue
        """
        Register the answer for a question given by the client in a queue,
        which holds the order in which the answers were registered.
        """
        self.queue_lock.acquire()
        self.answer_queue.put((client_socket, answer))
        self.queue_lock.release()

    def pick_random_question(self):
        """
        Pick and return a random question from the list of questions.
        """
        self.current_question = random.choice(questions)


    def getWinner(self):
        """
        If there is a winner, return them (IP address or something identifiable),
        if no winner, return None.
        """
        self.participations_lock.acquire()
        winner_name= self.participants[0][1]  # Return the address of the remaining participant
        self.participants[0][0].send(bytes("you won!", "utf-8"))
        self.participants[0][0].close()
        self.participations_lock.release()
        return winner_name
    def broadcast_udp(self):
        """
        Broadcast UDP offer messages to clients periodically.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_socket.bind((HOSTNAME, UDP_PORT))
            #TODO: validate packet size as in work instructions
            message = f"""Server here! Connect to me for trivia fun!
                        HOSTNAME: {HOSTNAME}
                        TCP PORT: {TCP_PORT}"""
            keepWaiting = True
            while keepWaiting:
                try:
                    udp_socket.sendto(message.encode(), ('<broadcast>', UDP_PORT))
                    print(f"Broadcast message sent! (time left: {self.waiting_time_left})")
                    time.sleep(BROADCAST_INTERVAL)
                    self.waiting_time_left  = self.waiting_time_left - 1
                    if self.waiting_time_left <= 0 & len(self.participants) == 0:
                        print(f"No participants have joined, restarting timer.")
                        keepWaiting = True
                        self.waiting_time_left = 10
                    elif self.waiting_time_left <= 0:
                        keepWaiting = False
                    else:
                        keepWaiting = True
                except Exception as e:
                    print(f"Error broadcasting: {e}")
            self.finished_recruiting = True
            with self.finished_recruiting_condition:
                self.finished_recruiting_condition.notify_all()

    def handle_client(self, client_socket: socket.socket, address: str):
        """
        Handle a connected client: manage their participation in the game, receive answers,
        and communicate game state changes.
        """
        try:
            print(f"Connection from {address} has been established.")
            client_socket.send(bytes("Please send your team name.", "utf-8"))
            team_name = client_socket.recv(1024).decode("utf-8").strip()
            
            # Register the participant
            with self.participations_lock:
                self.participants.append([client_socket, team_name, address, True])
                self.answers_dict[team_name] = None  # Initialize participant's answer state
            
            # Notify participant of game start
            client_socket.send(bytes("Welcome to the trivia game!", "utf-8"))
            
            # Wait for the game to start
            with self.game_started_condition:
                while not self.game_phase:
                    self.game_started_condition.wait()

            # Game has started, handle questions and answers
            while self.game_phase:
                with self.synchronize_round:
                    self.synchronize_round.wait()  # Synchronize with the game round

                if not self.isStillParticipating(team_name):
                    break  # If not participating, break the loop

                try:
                    # Send current question
                    question_text = self.current_question[0]  # Get the question text
                    client_socket.send(question_text.encode("utf-8"))
                    
                    # Set a timeout for client response
                    client_socket.settimeout(10)  # Set timeout to 10 seconds

                    # Receive response
                    response = client_socket.recv(1024).decode("utf-8").strip()
                    correct_answer = self.current_question[1]  # Get the correct answer

                    # Check and register the answer
                    if ((response == 'y' and correct_answer) or (response == 'n' and not correct_answer)):
                        self.answers_dict[team_name] = True  # Correct answer
                        client_socket.send(bytes("Correct answer!", "utf-8"))
                    else:
                        self.answers_dict[team_name] = False  # Incorrect answer
                        client_socket.send(bytes("Incorrect answer! You are out of the game.", "utf-8"))
                        with self.participations_lock:
                            for participant in self.participants:
                                if participant[1] == team_name:
                                    participant[3] = False  # Mark as no longer participating
                                    break

                    print(f"Response from {address}: {response} - {'Correct' if self.answers_dict[team_name] else 'Incorrect'}")

                except socket.timeout:
                    print(f"Timeout occurred while waiting for response from {address}")
                    with self.participations_lock:
                        for participant in self.participants:
                            if participant[1] == team_name:
                                participant[3] = False  # Mark as no longer participating
                                break
                    client_socket.send(bytes("No response received in time. You are out of the game.", "utf-8"))
                    break  # Exit the loop if a timeout occurs

                except Exception as e:
                    print(f"Error during the game phase with {address}: {e}")
                    break

        except Exception as e:
            print(f"Error handling client {address}: {e}")

        finally:
            if client_socket:
                client_socket.close()
                print(f"Connection with {address} has been closed.")

    def start_tcp_server(self):
        """
        Start the TCP server to accept client connections.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
                tcp_socket.bind((HOSTNAME, TCP_PORT))
                tcp_socket.listen(MAX_CONNECTIONS)
                print(f"TCP server listening on port {TCP_PORT}...")
                accepting_thread=threading.Thread(target=self.accept_participants,args=(tcp_socket,))
                accepting_thread.start()
                while not self.finished_recruiting:
                    with self.finished_recruiting_condition:
                        self.finished_recruiting_condition.wait()
                tcp_socket.close()          
        except Exception as e:
            print(e)
    def set_finished_recruiting(self,bool):
        self.finished_recruiting = bool
    def isFinished(self):
        self.get_active_paarticipants()
        self.participations_lock.acquire()
        answer= len(self.participants) == 1
        self.participations_lock.release()
        return answer
    def accept_participants(self,tcp_socket:socket.socket):
        while not self.finished_recruiting:
            try:
                client_socket, address = tcp_socket.accept()
                #TODO: make sure line below works so it finish recruite only when no one registered in 10 seconds
                self.waiting_time_left=10
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                client_thread.start()
            except:
                print("finished accepting clients" )
        
    def get_active_paarticipants(self):
        #TODO: remove function and usage as all players has to stay connected
        self.participations_lock.acquire()
        self.participants= [p for p in self.participants if p[3]]
        self.participations_lock.release()

            
if __name__ == "__main__":
    server=Server()
    while True:
        
        udp_thread = threading.Thread(target=server.broadcast_udp)
        udp_thread.start()

        tcp_server_thread = threading.Thread(target=server.start_tcp_server)
        tcp_server_thread.start()
        udp_thread.join()

        timer = threading.Timer(0.2, server.set_finished_recruiting,args=(True,))
        timer.start()
        tcp_server_thread.join()
        server.game_phase = True
        # time.sleep(105)
        #game phase
        while not server.isFinished():
            server.pick_random_question()
            with server.game_started_condition:
                server.game_started_condition.notify_all()
            with server.synchronize_round:
                server.synchronize_round.notify_all()
            time.sleep(10)
            server.endRound()
        winner=server.getWinner()
        print(f"winner is: {winner}")
        server.finishGame()

        
        


