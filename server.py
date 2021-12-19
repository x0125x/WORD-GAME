import socket
import _thread
from threading import Thread
from word_game import Player, Game
from config import MAX_LISTEN, MAX_PLAYERS, MIN_PLAYERS, MAX_QUEUE_TIME, \
    LOGIN_REGISTER_TABLE, LOGS_PATH, QUEUE
from collections import deque
import time
import tables
from website import run_website


HOST = '127.0.0.1'
PORT = 65432


class Queue:

    def __init__(self):
        self.queue = deque([])
        with open(f'{LOGS_PATH}/Queue.txt', 'a+', encoding='utf-8') as file:
            file.write(f'[Queue]: Queue has been created\n')

    def add_to_queue(self, player):
        self.queue.append(player)
        tables.add_to_table(QUEUE, {'username': player.username})
        player.in_queue = True
        with open(f'{LOGS_PATH}/Queue.txt', 'a+', encoding='utf-8') as file:
            file.write(f'[Queue]: Added player {player.username} to the queue\n')

    def remove_from_queue(self, player):
        try:
            self.queue.remove(player)
            tables.remove_from_table(QUEUE, {'username': player.username})
            player.in_queue = False
            with open(f'{LOGS_PATH}/Queue.txt', 'a+', encoding='utf-8') as file:
                file.write(f'[Queue]: Removed player {player.username}(#{player.id}) from the queue\n')
        except ValueError:
            with open(f'{LOGS_PATH}/Queue.txt', 'a+', encoding='utf-8') as file:
                file.write(f'[Queue]: Couldn\'t remove player {player.username}(#{player.id}) from the queue\n')

    def start_game(self, players):
        game = Game(players)
        games.append(game)
        game.run_game()
        games.remove(game)

    def create_game(self):
        tables.create_table(QUEUE, {'position': 'INTEGER PRIMARY KEY', 'username': 'TEXT(20) NOT NULL'})
        with open(f'{LOGS_PATH}/Queue.txt', 'a+', encoding='utf-8') as file:
            file.write('[Queue]: Looking for players\n')
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
                        player.client_socket.sendall(' \0'.encode())
                        players.append(player)
                    except:
                        self.remove_from_queue(player)
                        player.logout
                if MIN_PLAYERS <= len(players) <= MAX_PLAYERS:
                    new_game = Thread(target=self.start_game, args=(players,))
                    new_game.start()
                    with open(f'{LOGS_PATH}/Queue.txt', 'a+', encoding='utf-8') as file:
                        file.write('[Queue]: Queuing completed. A game will be launched.\n')
            if (time.time() - queue_time) >= MAX_QUEUE_TIME:
                with open(f'{LOGS_PATH}/Queue.txt', 'a+', encoding='utf-8') as file:
                    file.write('[Queue]: Queuing completed. Timed out.\n')


def is_game_active(game_id):
    for game in games:
        if game.id == game_id:
            return game
    return None


def start_new_connection(client_socket, client_addr, queue):
    player = Player(client_socket)
    try:
        player.login(players)
        if player.is_online:
            players.append(player)
            queue.add_to_queue(player)
            while (player.is_online and player.in_queue) or (player.is_online and player.in_game):
                try:
                    client_socket.sendall('\0'.encode())
                    time.sleep(1)
                except ConnectionAbortedError:
                    break
    except:
        pass
    if player is not None:
        if is_game_active(player.last_game_id):
            with open(f'{LOGS_PATH}/Game_{player.last_game_id}.txt', 'a+', encoding='utf-8') as file:
                file.write(f'[Game #{player.last_game_id}]: Player {player.username}(#{player.id}) has left the game\n')
        try:
            players.remove(player)
        except ValueError:
            pass
    if player is not None and player.is_online:
        if player.in_queue:
            queue.remove_from_queue(player)
        player.logout()
    elif player is None:
        client_socket.sendall('?\0'.encode())


def print_admin_cheatsheet():
    print('CHEATSHEET:\n'
          '[h] - show cheatsheet\n'
          '[r] - register user: r <username> <password>\n'
          '[d] - del user: d <username>\n'
          '[k] - kick user: k <username>\n'
          '[s] - stop game: s <game_id>\n')


def admin_console():
    while True:
        command = input('\n>> ').split(' ')
        if command[0] == 'h':
            print_admin_cheatsheet()
            continue
        elif command[0] == 'r':
            if len(command) != 3:
                print('Missing arguments!\n[h] - help')
                continue
            new_player = Player(None)
            new_player.register(command[1], command[2])
            del new_player
            continue
        if len(command) != 2:
            print('Missing arguments!\n[h] - help')
        elif command[0] == 'd':
            if tables.remove_from_table(LOGIN_REGISTER_TABLE, {'username': command[1]}):
                print(f'[Admin]: User {command[1]} has been deleted.')
                continue
            print(f'[Admin]: Error when deleting user {command[1]}. User not registered.')
        elif command[0] == 'k':
            for player in players:
                if player.username == command[1]:
                    player.logout()
        elif command[0] == 's':
            for game in games:
                if game.id == command[1]:
                    game.is_running = False


if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, PORT))
        except socket.error:
            print(socket.error)
        s.listen(MAX_LISTEN)
        queue = Queue()
        players = []
        games = []
        website_thread = _thread.start_new_thread(run_website, (queue,))
        queuing_system_thread = _thread.start_new_thread(queue.create_game, ())
        time.sleep(1)
        admin_console = _thread.start_new_thread(admin_console, ())
        while True:
            client_socket, client_addr = s.accept()
            _thread.start_new_thread(start_new_connection, (client_socket, client_addr, queue))
