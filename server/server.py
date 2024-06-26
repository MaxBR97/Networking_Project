import socket
import struct
import threading
import os
import sys
import time
import random
from question import questions
# Setup import paths
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)
from utils.network_utils import *

class Server():
    def __init__(self):
        # Initialization of server attributes
        self.udp_port=13117
        self.waiting_time_left_lock=threading.Lock()
        self.update_waiting_time_left()
        self.synchronize_round=threading.Condition()
        self.game_phase=False
        self.current_question=0
        self.finished_recruiting = False
        self.finished_recruiting_condition=threading.Condition()
        self.game_started_condition = threading.Condition()
        self.participations_lock = threading.Lock()
        self.participants = [] # element: [client_socket, address, still in game? (boolean)]
        self.answers_dict={}
        self.answers_lock=threading.Lock()
        self.total_questions={}
        self.corrected_questions={}
        self.total_questions_lock=threading.Lock()
        self.corrected_questions_lock=threading.Lock()
        self.tcp_server=find_available_port()
        self.hostname=get_local_ip()
        self.round_index=1
    
    def notify_synchronize_round(self):
        server.synchronize_round.acquire()
        server.synchronize_round.notify_all()
        server.synchronize_round.release()

    def notify_game_started_condition(self):
        server.game_started_condition.acquire()
        server.game_started_condition.notify_all()
        server.game_started_condition.release()

    def finishGame(self):
        """
        Restart variables to finish the game appropriately and be ready for another game.
        Resets the game state, clears participants, and prepares for a new game.
        """
        self.get_statictics()
        self.participations_lock.acquire()
        for participant in self.participants:
            participant[0].send(bytes(f"Game over! winner is {self.winner_name}", "utf-8"))  
            participant[0].close()
        self.participants=[]
        self.participations_lock.release()
        self.answers_lock.acquire()
        self.answers_dict={}
        self.answers_lock.release()
        self.game_phase = False
        self.update_waiting_time_left()
        self.current_question = 0  # Reset to the first question
        self.round_index=1
        self.finished_recruiting=False
        with self.synchronize_round:
            self.synchronize_round.notify_all()
    def update_waiting_time_left(self,time:int=10):
        self.waiting_time_left_lock.acquire()
        self.waiting_time_left = time
        self.waiting_time_left_lock.release()
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
        return False

    def endRound(self):
        """
        Calculate round results, expel players who answered wrong.
        """
        self.answers_lock.acquire()
        self.participations_lock.acquire()
        is_all_wrong=all(value == False for value in self.answers_dict.values())
        if not is_all_wrong:
            for team_name in self.answers_dict:
                answer = self.answers_dict[team_name]
                if not answer:
                    # Mark the participant as not participating anymore     
                    for participant in self.participants:
                        if participant[1]==team_name:
                            participant[3] = False  # Update participation status
        self.round_index+=1
        self.answers_dict={}
        self.participations_lock.release()
        self.answers_lock.release()
        

    def get_statictics(self):
        most_corrected_team=max(self.corrected_questions, key=lambda k: self.corrected_questions[k])
        most_correct_answers=self.corrected_questions[most_corrected_team]
        best_team_percentage,best_percentage=self.find_best_percentage_key()
        print(f"The team with most right answers is {most_corrected_team} with {most_correct_answers}")
        print(f"The team with the best percentage is {best_team_percentage} with {best_percentage}")
    def find_best_percentage_key(self):
        best_key = None
        best_percentage = 0
        for key in self.corrected_questions:
            if key in self.total_questions and self.total_questions[key] > 0:
                percentage = self.corrected_questions[key] / self.total_questions[key] * 100
                if percentage > best_percentage:
                    best_key = key
                    best_percentage = percentage
        return best_key,best_percentage

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
        participant=self.get_active_participants()
        self.winner_name= participant[0][1]  # Return the address of the remaining participant
        return self.winner_name
    
    def broadcast_udp(self):
        """
        Broadcast UDP offer messages to clients periodically with specific packet format.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_socket.bind((self.hostname, self.udp_port))

            # Prepare the message according to the specified packet format
            magic_cookie = 0xabcddcba
            message_type = 0x2
            server_name = "NBAQuiz"
            server_name_padded = server_name.ljust(32, '\0')  # Pad the server name to be 32 characters

            # Create the packet
            print(self.tcp_server)
            packet = struct.pack('!IB32sH', magic_cookie, message_type, server_name_padded.encode('utf-8'), self.tcp_server)
            keepWaiting = True
            while keepWaiting:
                try:
                    udp_socket.sendto(packet, ('<broadcast>', self.udp_port))
                    print(f"Broadcast message sent! (time left: {self.waiting_time_left})")
                    time.sleep(1)
                    self.update_waiting_time_left(self.waiting_time_left-1)
                    keepWaiting = False if self.waiting_time_left <= 0 else True
                    if not keepWaiting and len(self.participants)<=1:
                        if(self.participants == 1):
                            print(f"{self.participants} participant is connected. Waitning for at least 1 more participant.")
                        keepWaiting=True
                        self.update_waiting_time_left()
                except Exception as e:
                    print(f"Error broadcasting: {e}")
            self.finished_recruiting = True
            with self.finished_recruiting_condition:
                self.finished_recruiting_condition.notify_all()

    def handle_client(self, client_socket: socket.socket, address: str):
        """
        Handle a connected client.
        """
        try:
            print(f"Connection from {address} has been established.")
            ask_for_team_name="Please send your team name"
            print(ask_for_team_name)
            client_socket.send(bytes(ask_for_team_name, "utf-8"))
            team_name = client_socket.recv(1024).decode("utf-8").strip()
            self.participations_lock.acquire()
            self.participants.append([client_socket, team_name, address, True])
            self.participations_lock.release()

            # Wait until the game phase starts
            with self.game_started_condition:
                while not self.game_phase:
                    self.game_started_condition.wait()
                welcome_string="Welcome to the trivia game!"
                active_teams = self.get_active_participants()
                for i, team in enumerate(active_teams, 1):
                    welcome_string += f"Player {i}: {team[1]}\n"
                print(welcome_string)
                client_socket.send(bytes(welcome_string, "utf-8"))
                self.total_questions_lock.acquire()
                if team_name not in self.total_questions:
                    self.total_questions[team_name]=0
                self.total_questions_lock.release()
                self.corrected_questions_lock.acquire()
                if team_name not in self.corrected_questions:
                    self.corrected_questions[team_name]=0
                self.corrected_questions_lock.release()
            while self.game_phase:
                with self.synchronize_round:
                    self.synchronize_round.wait()

                if self.isStillParticipating(team_name):
                    try:
                        print(self.current_question)
                        self.total_questions_lock.acquire()
                        self.total_questions[team_name]+=1
                        self.total_questions_lock.release()
                        client_socket.send(self.current_question[0].encode("utf-8"))
                        client_socket.settimeout(9.5)  # Set timeout for client response
                        response = client_socket.recv(1024).decode("utf-8").strip()
                        user_response = response == 'y'
                        correct_answer = self.current_question[1] == user_response
                        self.answers_lock.acquire()
                        self.answers_dict[team_name] = correct_answer
                        self.answers_lock.release()
                        if correct_answer:
                            msg = f"{team_name} is correct!"
                            print(f"\033[92m{msg}\033[0m")  # Green text for correct answer
                            self.corrected_questions_lock.acquire()
                            self.corrected_questions[team_name]+=1
                            self.corrected_questions_lock.release()
                        else:
                            msg = f"{team_name} is incorrect."
                            print(f"\033[91m{msg}\033[0m")  # Red text for incorrect answer

                        print(f"Response from {address}: {response}")
                    except socket.timeout:
                        print(f"Timeout occurred while waiting for response from {address}")
                        msg = f"{team_name} is incorrect."
                        print(f"\033[91m{msg}\033[0m")  # Red text for incorrect answer
                        self.answers_lock.acquire()
                        self.answers_dict[team_name] = False
                        self.answers_lock.release()
                    except Exception as e:
                        print(f"Error during the game with {team_name}: {e}")
                        break
                else:
                    break
        except Exception as e:
            print(f"Error handling client {address}: {e}")


    def start_tcp_server(self):
        """
        Start the TCP server to accept client connections.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
                tcp_socket.bind((self.hostname, self.tcp_server))
                tcp_socket.listen(8)
                print(f"TCP server listening on port {self.tcp_server}...")
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
        participants=self.get_active_participants()
        answer= len(participants) == 1
        return answer
        
    def accept_participants(self,tcp_socket:socket.socket):
        while not self.finished_recruiting:
            try:
                client_socket, address = tcp_socket.accept()
                self.update_waiting_time_left()
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                client_thread.start()
            except:
                print("finished accepting clients" )
        
    def get_active_participants(self):
        self.participations_lock.acquire()
        participants= [p for p in self.participants if p[3]]
        self.participations_lock.release()
        return participants
        
    def start_round(self):
        active_teams=self.get_active_participants()
        active_team_names = " and ".join(team[1] for team in active_teams)
        self.participations_lock.acquire() 
        for participant in self.participants:
            start_round_str=f"Round {self.round_index}, played by {active_team_names}"
            print(start_round_str)
            participant[0].send(bytes(start_round_str, "utf-8"))  
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
        while not server.isFinished():
            if server.round_index!=1:
                server.start_round()
            server.pick_random_question()
            
            server.notify_game_started_condition()
            time.sleep(0.2)
            server.notify_synchronize_round()
            time.sleep(10)
            server.endRound()
        winner=server.getWinner()
        print(f"{winner} Wins!")
        server.finishGame()
