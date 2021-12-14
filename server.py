import socket
import _thread
from threading import Thread
from word_game import Player, Game
from config import MAX_LISTEN, MAX_PLAYERS, MIN_PLAYERS, MAX_QUEUE_TIME
from collections import deque
import time
from website import run_website


HOST = '127.0.0.1'
PORT = 65432


class Queue:

    def __init__(self):
        self.queue = deque([])
        print('[Queue]: Queue has been created')

    def add_to_queue(self, player):
        self.queue.append(player)
        player.in_queue = True
        print(f'[Queue]: Added player {player.username} to the queue')

    def remove_from_queue(self, player):
        try:
            self.queue.remove(player)
            player.in_queue = False
            print(f'[Queue]: Removed player {player.username} from the queue')
        except ValueError:
            print(f'[Queue]: couldn\'t remove player {player.username} from the queue')

    def start_game(self, players):
        game = Game(players)
        for i in range(1, 11).__reversed__():
            time.sleep(1)
            for player in players:
                player.client_socket.sendall(f'The game will start in: {str(i)}\n\0'.encode())
        games.append(game)
        game.run_game()
        games.remove(game)

    def create_game(self):
        print('[Queue]: Looking for players')
        while True:
            players = []
            queue_time = time.time()
            while len(self.queue) < MAX_PLAYERS and (time.time() - queue_time) < MAX_QUEUE_TIME:
                time.sleep(0.5)
            if len(self.queue) >= MIN_PLAYERS:
                while len(players) < MAX_PLAYERS:
                    if len(self.queue) == 0:
                        break
                    player = self.queue.popleft()
                    try:
                        with player.lock:
                            player.client_socket.sendall('Get ready. The game will start soon.\0'.encode())
                        players.append(player)
                    except:
                        self.remove_from_queue(player)
                        player.logout
                if MIN_PLAYERS <= len(players) <= MAX_PLAYERS:
                    new_game = Thread(target=self.start_game, args=(players,))
                    new_game.start()
                    print('[Queue]: Queuing completed. A game will be launched.')
            if (time.time() - queue_time) >= MAX_QUEUE_TIME:
                print('[Queue]: Queuing completed. Timed out.')
                for player in self.queue.__reversed__():
                    try:
                        with player.lock:
                            player.client_socket.sendall('There were not enough players '
                                                         'to start the game this time\0'.encode())
                    except:
                        self.remove_from_queue(player)
                        player.logout


def is_game_active(game_id):
    for game in games:
        if game.id == game_id:
            return game
    return None


def start_new_connection(client_socket, client_addr, queue):
    print(f'[Connection]: User {client_addr} connected')
    player = Player(client_socket)
    try:
        client_socket.sendall(f'Hello, {client_addr}!\nWelcome to the server!\n\n'
                              f'Choose one of the following options:\n'
                              f'[r] - register\n'
                              f'[l] - login\n\0'.encode())
        data = player.get_input('>> ', ['l', 'r'], 1, '\nMaximum number of tries reached. Disconnecting...')
        if data == 'l':
            player.login()
        elif data == 'r':
            player.register()
        if player.is_online:
            client_socket.sendall(f'Hello, {player.username}!\n\n\0'.encode())
            client_socket.sendall('Press CTRL-D at any point of time to logout.\0'.encode())
            while player.is_online:
                client_socket.sendall(f'Choose one of the following options:\n'
                                      f'[p] - play\n'
                                      f'[l] - logout\n\0'.encode())
                data = player.get_input('>> ', ['l', 'p'], 1, '\nMaximum number of tries reached. Disconnecting...')
                if data == 'l':
                    player.logout()
                elif data == 'p':
                    if not player.in_queue:
                        queue.add_to_queue(player)
                        client_socket.sendall(f'You have been added to the queue.\n'
                                              f'There are currently {len(queue.queue) - 1} '
                                              f'other players waiting.\0'.encode())
                    while (player.is_online and player.in_queue) or (player.is_online and player.in_game):
                        time.sleep(1)
    except:
        print(f'[Connection]: User {client_addr} unreachable')
        try:
            client_socket.sendall('Connection cannot be established. Quitting...\0'.encode())
        except socket.error:
            f'[Connection]: User {client_addr} encountered an socket error!\n{socket.error}'
    if player is None:
        client_socket.sendall('\0'.encode())
    elif player.is_online:
        if player.in_queue:
            queue.remove_from_queue(player)
        player.logout()
    print(f'[Connection]: User {client_addr} disconnected')


if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, PORT))
        except socket.error:
            print(socket.error)
        s.listen(MAX_LISTEN)
        print('[Server]: Server started')
        queue = Queue()
        games = []
        website_thread = _thread.start_new_thread(run_website, (queue,))
        queuing_system_thread = _thread.start_new_thread(queue.create_game, ())
        while True:
            # client_socket = new socket object
            # client_addr = tuple(client IP, TCP port number)
            client_socket, client_addr = s.accept()
            _thread.start_new_thread(start_new_connection, (client_socket, client_addr, queue))
