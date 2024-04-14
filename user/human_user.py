import sys
import os
from inputimeout import inputimeout #run pip install inputimeout
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)
from client.client import run_client
# Fill with names
names_array = ["Roee", "Maxim", "Idan", "Yossi", "Gal", "Lebron","Kobe", "Luka", "Magic"]

def handle_user_input(tcp_socket):   
    try:
        is_answer_fit=False
        while not is_answer_fit:
            user_input = inputimeout(prompt='true (y) or false (n):', timeout=9.5)
            if user_input in ['y', 'n']:
                is_answer_fit=True
                data_to_send = user_input.encode('utf-8')
                tcp_socket.send(data_to_send)
            else:
                print("Please enter a valid input ('y' or 'n').")
    except:
        print("time is up")


if __name__ == "__main__":
    run_client(handle_user_input,names_array)
