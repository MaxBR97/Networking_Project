import socket
import threading
import time
import random
from queue import Queue
from question import questions

# Constants
UDP_PORT = 13117
TCP_PORT = 12345
BROADCAST_INTERVAL = 1  # Seconds between broadcasts
MAX_CONNECTIONS = 8  # Maximum number of simultaneous client connections
HOSTNAME = "10.100.102.5"





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
    def finishGame(self):
        """
        Restart variables to finish the game appropriately and be ready for another game.
        Resets the game state, clears participants, and prepares for a new game.
        """
        self.participations_lock.acquire()
        self.participants.clear()
        self.participations_lock.release()
        self.game_phase = False
        self.waiting_time_left = 10  # Reset waiting time
        self.current_question = 0  # Reset to the first question

    def isStillParticipating(self, team_name:str):
        """
        Return true if client_socket is still participating, meaning they didn't answer wrong so far.
        """
        self.participations_lock.acquire()
        for participant in self.participants:
            if participant[1]==team_name:
                self.participations_lock.release()
                return participant[3]  # The boolean flag for participation
        self.participations_lock.release()
        print(f"isStillParticipating return {False}")
        return False

    def endRound(self):
        """
        Calculate round results, expel players who answered wrong.
        """
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
                        participant[0].close()
                        break
                self.participations_lock.release()
            else:
                print(f"{team_name} is correct!")
        self.queue_lock.release()

    def registerAnswer(self,client_socket, answer):
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
        self.participations_lock.release()
        return winner_name
    def broadcast_udp(self):
        """
        Broadcast UDP offer messages to clients periodically.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_socket.bind((HOSTNAME, UDP_PORT))
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
                    keepWaiting = False if self.waiting_time_left <= 0 else True
                except Exception as e:
                    print(f"Error broadcasting: {e}")
            self.finished_recruiting = True
            with self.finished_recruiting_condition:
                self.finished_recruiting_condition.notify_all()

    def handle_client(self,client_socket:socket.socket, address:str):
        """
        Handle a connected client.
        """
        try:
            print(f"Connection from {address} has been established.")
            client_socket.send(bytes("please send your team name", "utf-8"))
            team_name = client_socket.recv(1024).decode("utf-8")
            self.participations_lock.acquire()
            self.participants.append([client_socket,team_name, address, True])
            self.participations_lock.release()
            client_socket.send(bytes("Welcome to the trivia game!", "utf-8"))
            with self.game_started_condition:
                while not self.game_phase:
                    self.game_started_condition.wait()
            while self.game_phase:
                if self.isStillParticipating(team_name):
                    startTime = time.thread_time_ns()
                    try:
                        with self.synchronize_round:
                            self.synchronize_round.wait()
                        print(self.current_question)
                        client_socket.send(self.current_question[0].encode("utf-8"))
                        client_socket.settimeout(10 - time.thread_time_ns + startTime)
                        response = client_socket.recv(1024).decode("utf-8")
                        self.registerAnswer(team_name, response)
                        print(f"Response from {address}: {response}")
                    except socket.timeout:
                        print(f"Timeout occurred while waiting for response from {address}")
                        break  # Exit the loop if a timeout occurs
                    except Exception as e:
                        print(f"removed {team_name}")
                else:
                    client_socket.send(bytes("you are out of the game, you have lost", "utf-8"))
                    break
                
            # Here, you would add the logic to interact with the client during the game.
        except Exception as e:
            print(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()

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
                        time.sleep(8)
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
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                client_thread.start()
            except:
                print("finished accepting clients" )
        
    def get_active_paarticipants(self):
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

        
        


