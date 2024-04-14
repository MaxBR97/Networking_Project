import sys
import os
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)
from client.client import run_client
import random
import socket
bot_names_array = [
    "BOT:Lebron", 
    "BOT:Kobe", 
    "BOT:Michael", 
    "BOT:Steph", 
    "BOT:Kawhi", 
    "BOT:Giannis", 
    "BOT:Kevin", 
    "BOT:Russell", 
    "BOT:Anthony", 
    "BOT:James"
]

def bot_behavior(tcp_socket: socket):
    """
    Defines the bot's behavior during the game.
    """
    answer = random.choice(['y', 'n'])
    print(f"Bot automatically answering: {answer}")
    tcp_socket.send(answer.encode('utf-8'))


if __name__ == "__main__":
    run_client(bot_behavior,bot_names_array)
