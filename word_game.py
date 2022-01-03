import re
import time
import mmap
import binascii
import hashlib
import tables
from config import *
import socket
from threading import Lock
from io import open
from random import randint


class Player:

    def __init__(self, client_socket, username=None, hash_passwd=None):
        self.id = None
        self.score = 0
        self.in_game = False
        self.in_queue = False
        self.last_game_id = None
        self.round_points = 0
        self.username = username
        self.password = hash_passwd
        self.lock = Lock()
        self.client_socket = client_socket
        self.is_online = False
        self.guessed = ''
        self.display_word = None
        self.num_of_games = 0
        self.average_score = '0'

    def update_data(self):
        data = list(tables.is_in_table(LOGIN_REGISTER_TABLE, {'username': self.username, 'password': self.password}))
        self.id = data[0]
        self.username = data[1]
        self.password = data[2]
        self.score = data[3]
        self.num_of_games = data[4]
        self.average_score = data[5]
        self.last_game_id = data[6]
        if self.last_game_id == -1:
            self.last_game_id = None
        return self

    def update_db(self, game_id):
        tables.update_table(LOGIN_REGISTER_TABLE, {'score': self.score,
                                                   'number_of_games': self.num_of_games,
                                                   'average_score': self.average_score,
                                                   'last_game_id': int(game_id)},
                            f'user_id={self.id}')

    def add_points(self, points):
        self.round_points += points

    def update_score(self):
        self.score += self.round_points
        self.round_points = 0
        self.num_of_games += 1
        self.average_score = '{:.2f}'.format(self.score/self.num_of_games)
        self.update_db(self.last_game_id)

    def check_status(self):
        if self.is_online:
            return self
        return None

    def start_game(self, game_id):
        self.round_points = 0
        self.guessed = ''
        self.display_word = None
        self.last_game_id = game_id
        self.in_game = True
        self.in_queue = False

    def logout(self):
        self.is_online = False
        try:
            time.sleep(0.1)
            self.client_socket.sendall('?\0'.encode())
            self.client_socket.shutdown(socket.SHUT_RDWR)
            self.client_socket.close()
            with open(f'{LOGS_PATH}/{self.username}.txt', 'a+', encoding='utf-8') as file:
                file.write(f'[Access]: Player {self.username}(#{self.id}) has logged out.\n')
        except ConnectionAbortedError or ConnectionResetError:
            pass

    def get_input(self, message, valid_chars, max_len, err_msg=None, lower=True):
        if message is not None:
            message = message + '\0'
        with self.lock:
            if not isinstance(max_len, int) or max_len > MAX_INPUT_LEN:
                max_len = MAX_INPUT_LEN
            try:
                if message is not None:
                    self.client_socket.sendall(message.encode())
                self.client_socket.settimeout(KICK_TIME)
                reply_time = time.time()
                try:
                    inp = self.client_socket.recv(SIZE_OF_DATA).decode()
                    if lower:
                        inp = inp.lower()
                except socket.timeout:
                    with open(f'{LOGS_PATH}/{self.username}.txt', 'a+', encoding='utf-8') as file:
                        file.write(f'[Input]: Player {self.username}(#{self.id}) has failed to reply '
                                   f'in time and is being kicked.\n')
                    self.logout()
                    return None
                reply_time = time.time() - reply_time

                if reply_time > IGNORE_TIME:
                    self.client_socket.sendall('#\0'.encode())
                    with open(f'{LOGS_PATH}/{self.username}.txt', 'a+', encoding='utf-8') as file:
                        file.write(f'[Input]: Player {self.username}(#{self.id}) has failed to reply '
                                   f'in time and is being ignored.\n')
                    return None

                valid = True
                if len(inp) > max_len:
                    with open(f'{LOGS_PATH}/{self.username}.txt', 'a+', encoding='utf-8') as file:
                        file.write(f'[Input]: Player {self.username}(#{self.id}) has tried to '
                                   f'type in an overly long input "{inp}" and is now being kicked out of the server.\n')
                    valid = False
                if inp is None:
                    valid = False
                else:
                    for letter in inp:
                        if letter not in valid_chars:
                            self.client_socket.sendall('?\0'.encode())
                            with open(f'{LOGS_PATH}/{self.username}.txt', 'a+', encoding='utf-8') as file:
                                file.write(f'[Input]: Player {self.username}(#{self.id}) has tried to '
                                           f'type in an invalid char "{letter}" and is now being kicked '
                                           f'out of the server.\n')
                            valid = False
                if valid:
                    return inp[:-1]
                if err_msg is not None:
                    err_msg = err_msg + '\0'
                    self.client_socket.sendall(err_msg.encode())
                self.logout()
                return None
            except ConnectionAbortedError or ConnectionResetError:
                self.logout()
                return None
            self.logout()
            return None

    @staticmethod
    def get_hashed_password(password):
        if password is None:
            return None
        return binascii.hexlify(hashlib.pbkdf2_hmac(HASH_METHOD, password.encode(), SALT, ITERATIONS)).decode()

    # adds provided data to a database and returns a Player object
    def register(self, username=None, passwd=None):
        args = {'user_id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                'username': f'TEXT({USERNAME_MAX_LEN}) NOT NULL',
                'password': f'TEXT({PASSWORD_MAX_LEN}) NOT NULL',
                'score': 'INTEGER DEFAULT 0',
                'number_of_games': 'INTEGER DEFAULT 0',
                'average_score': 'TEXT DEFAULT \'0\'',
                'last_game_id': 'INTEGER DEFAULT -1'}

        tables.create_table(LOGIN_REGISTER_TABLE, args)
        while username is None:
            username = self.get_input('Choose a unique username: ', ALPHABET + DIGITS, USERNAME_MAX_LEN)
            if tables.is_in_table(LOGIN_REGISTER_TABLE, {'username': username}) is not None:
                self.client_socket.sendall('Username already taken. Try again.\0'.encode())
                username = None
        self.username = username

        while passwd is None:
            passwd = self.get_input('Choose password: ', ALPHABET + DIGITS, PASSWORD_MAX_LEN)
            retype_passwd = self.get_input('Retype the password: ', ALPHABET + DIGITS, PASSWORD_MAX_LEN)
            if passwd == retype_passwd:
                break
            self.client_socket.sendall('Passwords not matching. Try again.\0'.encode())
        self.password = self.get_hashed_password(passwd)

        tables.add_to_table(LOGIN_REGISTER_TABLE, {'username': self.username, 'password': self.password})
        self.is_online = True
        player = self.update_data()
        with open(f'{LOGS_PATH}/{self.username}.txt', 'a+', encoding='utf-8') as file:
            file.write(f'[Access]: Player {self.username}(#{self.id}) has been registered\n')
        return player

    @staticmethod
    def is_login_successful(table_name, username, passwd):
        if tables.is_in_table(table_name, {'username': username, 'password': passwd}, 'username, password'):
            return True
        return False

    def is_player_online(self, players):
        for player in players:
            if player.id == self.id:
                return True
        return False

    def login(self, players):
        data = self.get_input(None, ALPHABET + ALPHABET.upper() + DIGITS + END_OF_LINE,
                              USERNAME_MAX_LEN + PASSWORD_MAX_LEN + 2, lower=False).replace('\n', '\0').split('\0')
        username, passwd = data[0], data[1]
        if username is None:
            return None
        passwd = self.get_hashed_password(passwd)
        if passwd is None:
            return None
        if self.is_login_successful(LOGIN_REGISTER_TABLE, username, passwd):
            self.username = username
            self.password = passwd
            self.is_online = True
            self.update_data()
            if not self.is_player_online(players):
                self.client_socket.sendall('+1\0'.encode())
                with open(f'{LOGS_PATH}/{self.username}.txt', 'a+', encoding='utf-8') as file:
                    file.write(f'[Access]: Player {self.username}(#{self.id}) has logged in\n')
                return self
        self.client_socket.sendall('-\0'.encode())
        with open(f'{LOGS_PATH}/{username}.txt', 'a+', encoding='utf-8') as file:
            file.write(f'[Access]: Player {username} has failed to log in.\n')
        time.sleep(0.1)
        self.logout()
        return None


class Game:

    def __init__(self, players=None, _id=None):
        self.word = None
        self.lock = Lock()
        self.display_word = None
        self.recent_guess = None
        self.players = players
        self.guessing_players = None
        self.id = _id
        self.is_running = False
        self.options = {'+': self.guess_letter,
                        '=': self.guess_word}
        tables.create_table(GAME_HISTORY_TABLE, {'game_id': 'INTEGER PRIMARY KEY',
                                                 'selected_word': 'TEXT',
                                                 'num_of_players': 'INTEGER',
                                                 'players_guessing_id': 'TEXT',
                                                 'winner': 'TEXT'})

    def set_word(self, player):
        word = player.get_input('@', ALPHABET + END_OF_LINE, MAX_INPUT_LEN)
        if word is not None:
            with open(DICT_PATH) as dict_, mmap.mmap(dict_.fileno(), 0, access=mmap.ACCESS_READ) as dict_content:
                if dict_content.find(word.lower().encode()) != -1:
                    self.word = word.lower()
                    display_word = ''
                    for letter in self.word:
                        if letter in LETTERS_1LINE:
                            display_word += '1'
                        elif letter in LETTERS_2LINE:
                            display_word += '2'
                        elif letter in LETTERS_3LINE:
                            display_word += '3'
                        elif letter in LETTERS_4LINE:
                            display_word += '4'
                        else:
                            player.logout()
                            raise ValueError(f'Character {letter} not recognised.')
                            return False
                else:
                    with open(f'{LOGS_PATH}/Game_{self.id}.txt', 'a+', encoding='utf-8') as file:
                        file.write(f'[Game #{self.id}]: Word "{word.lower()}" selected by player '
                                   f'{player.username}(#{player.id}) is not recognised - '
                                   f'player is being kicked out of the server.\n')
                    player.logout()
                    return False
            with open(f'{LOGS_PATH}/Game_{self.id}.txt', 'a+', encoding='utf-8') as file:
                file.write(f'[Game #{self.id}]: The word "{self.word}" has been chosen by '
                           f'player {player.username}(#{player.id}) for this round.\n')
            for player in self.players:
                player.display_word = display_word
            return True
        return False

    def update_display_word_and_recent_guess(self, player):
        for i in range(len(self.word)):
            if player.display_word[i] in '1234' and self.word[i] in player.guessed:
                player.display_word = player.display_word[:i] + self.word[i] + player.display_word[i+1:]
                self.recent_guess = self.recent_guess[:i] + '1' + self.recent_guess[i+1:]

    @staticmethod
    def send_to_all(players, message):
        message = message + '\0'
        if not isinstance(players, list):
            try:
                players = list(players)
            except TypeError:
                players = [players]
        for player in players:
            try:
                player.client_socket.sendall(message.encode())
            except:
                pass

    def guess_letter(self, player, letter):
        self.recent_guess = '0' * len(self.word)

        if letter is not None:
            letter = letter.lower()
            if letter in self.word and letter not in player.guessed:
                player.guessed += letter
                points = self.word.count(letter) * GUESS_LETTER_POINTS
                player.add_points(points)
                self.update_display_word_and_recent_guess(player)
                if not re.search('[1-4]+', player.display_word):
                    tables.update_table(GAME_HISTORY_TABLE, {'winner': player.username}, f'game_id={self.id}')
                    self.is_running = False
                    with open(f'{LOGS_PATH}/Game_{self.id}.txt', 'a+', encoding='utf-8') as file:
                        file.write(f'[Game #{self.id}]: Player {player.username}(#{player.id}) '
                                   f'has guessed all letters\n')
                player.client_socket.sendall(f'=\n{self.recent_guess}\0'.encode())
                return True
        player.client_socket.sendall('!\0'.encode())
        return False

    def guess_word(self, player, word):
        if word is None:
            return False
        if word.lower() == self.word:
            self.display_word = self.word.replace
            player.add_points(GUESS_WORD_POINTS)
            with open(f'{LOGS_PATH}/Game_{self.id}.txt', 'a+', encoding='utf-8') as file:
                file.write(f'[Game #{self.id}]: Player {player.username}(#{player.id}) has guessed the word\n')
            for player in self.players:
                player.client_socket.sendall(f'=\n{player.round_points}\n?\0'.encode())
            tables.update_table(GAME_HISTORY_TABLE, {'winner': player.username}, f'game_id={self.id}')
            self.is_running = False
            return True
        player.client_socket.sendall('!\0'.encode())
        return False

    def get_option(self, player):
        try:
            inp = player.get_input(None, ALPHABET + "".join(self.options.keys()) + END_OF_LINE,
                                   100).replace('\n', '\0').replace('\0', '')
            return inp[0], inp[1:]
        except IndexError or AttributeError:
            player.logout()
            return None, None

    def perform_option(self, player, option, val):
        try:
            return self.options[option](player, val)
        except KeyError:
            return False

    def print_and_update_scores(self):
        with open(f'{LOGS_PATH}/Game_{self.id}.txt', 'a+', encoding='utf-8') as file:
            file.write(f'[Game #{self.id}]: The game has finished\n')
            for player in self.players:
                file.write(f'[Game #{self.id}]: Player {player.username}(#{player.id}) scored: {player.round_points}\n')
                try:
                    player.client_socket.sendall(f'=\n{player.round_points}\n?\0'.encode())
                except ConnectionAbortedError:
                    pass
                player.update_score()

    def initialize_the_game(self):
        self.create_record_and_set_id()
        for player in self.players:
            player.start_game(self.id)
        self.is_running = True

    def create_record_and_set_id(self):
        with self.lock:
            self.id = tables.add_to_table(GAME_HISTORY_TABLE, {'num_of_players': len(self.players),
                                                               'players_guessing_id': '[NOT SET]',
                                                               'selected_word': '[NOT SET]'})
            with open(f'{LOGS_PATH}/Game_{self.id}.txt', 'a+', encoding='utf-8') as file:
                file.write(f'[Game #{self.id}]: Game has been added to the history\n')

    def update_history(self):
        with self.lock:
            tables.update_table(GAME_HISTORY_TABLE, {'selected_word': self.word,
                                                     'players_guessing_id':
                                                         '\n'.join([str(p.username) for p in self.players])},
                                f'game_id={self.id}')
            with open(f'{LOGS_PATH}/Game_{self.id}.txt', 'a+', encoding='utf-8') as file:
                file.write(f'[Game #{self.id}]: Data has been updated"\n')

    def reset_game_values(self):
        self.word = None
        self.display_word = None
        self.recent_guess = None
        self.is_running = False
        for player in self.players:
            player.in_game = False

    def rejoin_player(self, rejoined_player):
        for player in self.players:
            if player.id == rejoined_player.id:
                player = rejoined_player
                player.in_game = True
                self.guessing_players.append(rejoined_player.id)
                with open(f'{LOGS_PATH}/Game_{self.id}.txt', 'a+', encoding='utf-8') as file:
                    file.write(
                        f'[Game #{self.id}]: Player {player.username}(#{player.id}) has rejoined the game\n')

    @staticmethod
    def build_dict():
        file = open(DICT_PATH, mode='r', encoding='utf8')
        mapped_file = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        dictionary = {}
        line_content = mapped_file.readline().decode()[:-2]
        line_num = 0
        while line_content:
            if len(line_content) > 4:
                dictionary[line_num] = line_content
                line_num += 1
            line_content = mapped_file.readline().decode()[:-2]
        return dictionary

    def select_word(self):
        dictionary = self.build_dict()
        line_num = randint(0, len(dictionary))
        word = dictionary[line_num]
        self.word = word
        display_word = ''
        for letter in self.word:
            if letter in LETTERS_1LINE:
                display_word += '1'
            elif letter in LETTERS_2LINE:
                display_word += '2'
            elif letter in LETTERS_3LINE:
                display_word += '3'
            elif letter in LETTERS_4LINE:
                display_word += '4'
            else:
                self.select_word()
        self.display_word = display_word
        for player in self.players:
            player.display_word = display_word
            player.client_socket.sendall(f'{player.display_word}\0'.encode())
        with open(f'{LOGS_PATH}/Game_{self.id}.txt', 'a+', encoding='utf-8') as file:
            file.write(f'[Game #{self.id}]: Word "{word}" has been selected for the game\n')

    def run_game(self):
        self.initialize_the_game()
        self.guessing_players = [p.id for p in self.players]
        self.select_word()
        self.update_history()
        round = 0
        while self.is_running and round < 10:
            for player in self.players:
                if len(self.guessing_players) < 1:
                    self.is_running = False
                    break
                if player.id not in self.guessing_players:
                    continue
                if not player.is_online:
                    try:
                        self.guessing_players.remove(player.id)
                    except ValueError:
                        pass
                    continue
                if not self.is_running:
                    break
                opt, val = self.get_option(player)
                with open(f'{LOGS_PATH}/Game_{self.id}.txt', 'a+', encoding='utf-8') as file:
                    file.write(f'[Game #{self.id}]: Player {player.username}(#{player.id}) tried:'
                               f' option "{opt}" with value: "{val}"\n')
                if opt in self.options.keys():
                    if not self.perform_option(player, opt, val):
                        continue
                self.recent_guess = None
                round += 1
        self.print_and_update_scores()
        self.reset_game_values()
