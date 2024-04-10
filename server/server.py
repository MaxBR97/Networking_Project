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
import utils.network_utils 


# Constants
UDP_PORT = 13117
# TODO: make those dynamic and remove Constants maybe use find_available_port function from above
TCP_PORT = utils.network_utils.find_available_port()
HOSTNAME = utils.network_utils.get_local_ip()
BROADCAST_INTERVAL = 1  # Seconds between broadcasts
MAX_CONNECTIONS = 8  # Maximum number of simultaneous client connections


# Use a lock for thread-safe operations on shared resources


class Server():
    def __init__(self):
        self.udp_port = 13117
        self.waiting_time_left = 10
        self.answer_queue = Queue()  # To store answers in the order they're received
        self.synchronize_round = threading.Condition()
        self.game_phase = False
        self.current_question = 0
        self.finished_recruiting = False
        self.finished_recruiting_condition = threading.Condition()
        self.game_started_condition = threading.Condition()
        self.participations_lock = threading.Lock()
        # element: [client_socket, address, still in game? (boolean)]
        self.participants = []
        self.queue_lock = threading.Lock()
        self.answers_dict = {}
        self.answers_lock = threading.Lock()
        # TODO: Bonus add to those so we can have statictics and print/print and send those at the end of every game
        self.total_questions = {}
        self.corrected_questions = {}
        self.total_questions_lock = threading.Lock()
        self.corrected_questions_lock = threading.Lock()

    def finishGame(self):
        """
        Restart variables to finish the game appropriately and be ready for another game.
        Resets the game state, clears participants, and prepares for a new game.
        """
        self.participations_lock.acquire()
        self.participants = []
        self.participations_lock.release()
        self.game_phase = False
        self.waiting_time_left = 10  # Reset waiting time
        self.current_question = 0  # Reset to the first question
        self.finished_recruiting = False
        with self.synchronize_round:
            self.synchronize_round.notify_all()

    def isStillParticipating(self, team_name: str):
        """
        Return true if client_socket is still participating, meaning they didn't answer wrong so far.
        """
        self.participations_lock.acquire()
        for participant in self.participants:
            if participant[1] == team_name:
                self.participations_lock.release()
                print(participant[3])
                return participant[3]  # The boolean flag for participation
        self.participations_lock.release()
        print(False)
        return False


    def endRound(self):
        """
        Calculate round results, expel players who answered incorrectly based on the dictionary entries.
        """
        self.answers_lock.acquire()
        # Assuming questions are [question_text, true/false_answer]
        correct_answer = questions[self.current_question][1]
        for team_name, answer in self.answers_dict.items():
            if (answer == 'y' and not correct_answer) or (answer == 'n' and correct_answer):
                print(f"{team_name} is wrong.")
                self.participations_lock.acquire()
                for participant in self.participants:
                    if participant[1] == team_name:
                        participant[3] = False
                        participant[0].send(
                            "You are out of the game, you have lost.".encode('utf-8'))
                        participant[0].close()
                        break
                self.participations_lock.release()
            else:
                print(f"{team_name} answered correctly!")
        self.answers_dict.clear()
        self.answers_lock.release()

    def registerAnswer(self, team_name, answer):
        """
        Register the answer for a question given by the client in a dictionary,
        which tracks answers by team name.
        """
        self.answers_lock.acquire()
        self.answers_dict[team_name] = answer
        self.answers_lock.release()

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
        # Return the address of the remaining participant
        winner_name = self.participants[0][1]
        self.participants[0][0].send(bytes("you won!", "utf-8"))
        self.participants[0][0].close()
        self.participations_lock.release()
        return winner_name


    def broadcast_udp(self):
        """
        Broadcast UDP offer messages to clients periodically.
        Dynamically adjust UDP and TCP ports and validate packet size.
        """
        # Dynamically find available ports for UDP and TCP (Assuming find_available_port() is correctly implemented)
        self.udp_port = self.find_available_port()
        global TCP_PORT
        TCP_PORT = self.find_available_port()

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_socket.bind((HOSTNAME, self.udp_port))  # Bind using the dynamically found UDP port
            
            message = f"Server here! Connect to me for trivia fun! HOSTNAME: {HOSTNAME} TCP PORT: {TCP_PORT}"
            if len(message.encode('utf-8')) > 508:
                print("Error: Broadcast message size exceeds the safe UDP packet size limit.")
                return  # Exit if the message is too large to safely send
            
            print(f"Broadcasting on UDP port {self.udp_port} and TCP port {TCP_PORT}")
            
            keepBroadcasting = True
            while keepBroadcasting:
                try:
                    udp_socket.sendto(message.encode('utf-8'), ('<broadcast>', self.udp_port))
                    print(f"Broadcast message sent! Time left: {self.waiting_time_left}s")
                    time.sleep(BROADCAST_INTERVAL)
                    self.waiting_time_left -= 1
                    if self.waiting_time_left <= 0:
                        if len(self.participants) == 0:
                            print("No participants have joined, restarting broadcast.")
                            self.waiting_time_left = 10  # Reset the timer if no participants have joined
                        else:
                            keepBroadcasting = False
                except Exception as e:
                    print(f"Error broadcasting: {e}")
                    break

            self.finished_recruiting = True
            with self.finished_recruiting_condition:
                self.finished_recruiting_condition.notify_all()




    def handle_client(self, client_socket, address):
        """
        Handle a connected client by managing their participation in the trivia game.
        """
        try:
            # First, get the team name from the client
            team_name = client_socket.recv(1024).decode("utf-8").strip()
            print(f"Connection from {team_name}@{address} established.")

            # Register the client
            self.participations_lock.acquire()
            self.participants.append([client_socket, team_name, address, True])
            self.participations_lock.release()

            # Wait for the game to start before sending the welcome message
            with self.game_started_condition:
                while not self.game_phase:
                    self.game_started_condition.wait()
            client_socket.send("Welcome to the trivia game!".encode('utf-8'))

            # Game loop: continue while the game phase is active
            while self.game_phase:
                with self.synchronize_round:
                    self.synchronize_round.wait()

                if self.isStillParticipating(team_name):
                    question_text = questions[self.current_question][0]
                    client_socket.send(question_text.encode('utf-8'))

                    # Set a timeout for client response
                    client_socket.settimeout(10)  # Wait for up to 10 seconds for a response

                    try:
                        response = client_socket.recv(1024).decode("utf-8").strip()
                        print(f"{team_name} answered: {response}")

                        # Register the answer using the revised approach
                        self.registerAnswer(team_name, response)

                    except socket.timeout:
                        print(f"Timeout occurred while waiting for response from {team_name}")
                        # Mark the participant as not participating if they time out
                        self.participations_lock.acquire()
                        for participant in self.participants:
                            if participant[1] == team_name:
                                participant[3] = False  # Set their game participation to False
                                break
                        self.participations_lock.release()

                    except Exception as e:
                        print(f"Error receiving response from {team_name}: {e}")

                else:
                    # If not participating, skip to the next participant
                    continue

        except Exception as e:
            print(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()
            print(f"Closed connection to {team_name}@{address}")


    def start_tcp_server(self):
        """
        Start the TCP server to accept client connections.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
                tcp_socket.bind((HOSTNAME, TCP_PORT))
                tcp_socket.listen(MAX_CONNECTIONS)
                print(f"TCP server listening on port {TCP_PORT}...")
                accepting_thread = threading.Thread(
                    target=self.accept_participants, args=(tcp_socket,))
                accepting_thread.start()
                while not self.finished_recruiting:
                    with self.finished_recruiting_condition:
                        self.finished_recruiting_condition.wait()
                tcp_socket.close()
        except Exception as e:
            print(e)

    def set_finished_recruiting(self, bool):
        self.finished_recruiting = bool

    def isFinished(self):
        self.get_active_participants()
        self.participations_lock.acquire()
        answer = len(self.participants) == 1
        self.participations_lock.release()
        return answer

    def accept_participants(self, tcp_socket: socket.socket):
        last_connection_time = time.time()
        while not self.finished_recruiting:
            try:
                tcp_socket.settimeout(10)  # Set a timeout for accepting new connections
                client_socket, address = tcp_socket.accept()
                last_connection_time = time.time()  # Reset last connection time on new connection
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                client_thread.start()
            except socket.timeout:
                if time.time() - last_connection_time >= 10:
                    print("No new participants in the last 10 seconds, finishing recruitment.")
                    break
            except Exception as e:
                print(f"Exception in accepting clients: {e}")
                break


    def get_active_participants(self):
        """
        Update the participants list to only include those who are still active and connected.
        """
        active_participants = []
        self.participations_lock.acquire()
        try:
            for participant in self.participants:
                client_socket, team_name, address, is_still_in_game = participant
                if is_still_in_game:
                    try:
                        # Check if the socket is still connected by attempting a non-blocking, non-data-receiving call
                        client_socket.setblocking(0)
                        if client_socket.recv(1, socket.MSG_PEEK) == b'':
                            is_still_in_game = False  # No data and no blocking means disconnected
                    except BlockingIOError:
                        # No data ready to be received; continue
                        pass
                    except ConnectionResetError:
                        is_still_in_game = False  # Connection was reset, so mark as not in game
                    finally:
                        client_socket.setblocking(1)  # Restore blocking mode

                if is_still_in_game:
                    active_participants.append(participant)
                else:
                    client_socket.close()  # Close the socket if no longer active

            self.participants = active_participants  # Update the main list with only active participants
        finally:
            self.participations_lock.release()


if __name__ == "__main__":
    server = Server()
    while True:

        udp_thread = threading.Thread(target=server.broadcast_udp)
        udp_thread.start()

        tcp_server_thread = threading.Thread(target=server.start_tcp_server)
        tcp_server_thread.start()
        udp_thread.join()

        timer = threading.Timer(
            0.2, server.set_finished_recruiting, args=(True,))
        timer.start()
        tcp_server_thread.join()
        server.game_phase = True
        # time.sleep(105)
        # game phase
        while not server.isFinished():
            server.pick_random_question()
            with server.game_started_condition:
                server.game_started_condition.notify_all()
            with server.synchronize_round:
                server.synchronize_round.notify_all()
            time.sleep(10)
            server.endRound()
        winner = server.getWinner()
        print(f"winner is: {winner}")
        server.finishGame()
