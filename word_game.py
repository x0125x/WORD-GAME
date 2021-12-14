import re
import time
import mmap
import binascii
import hashlib
import tables
from config import *
import socket
from threading import Lock
import copy


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

    def update_data(self):
        data = list(tables.is_in_table(LOGIN_REGISTER_TABLE, {'username': self.username, 'password': self.password}))
        self.id = data[0]
        self.username = data[1]
        self.password = data[2]
        self.score = data[3]
        self.last_game_id = data[4]
        if self.last_game_id == -1:
            self.last_game_id = None
        # TODO: check if game running to update other values and go back to game
        return self

    def update_db(self, game_id):
        tables.update_table(LOGIN_REGISTER_TABLE, {'score': self.score,
                                                   'last_game_id': int(game_id)},
                            f'user_id={self.id}')

    def add_points(self, points):
        self.round_points += points

    def update_score(self):
        self.score += self.round_points
        self.round_points = 0
        self.update_db(self.last_game_id)

    def check_status(self):
        if self.is_online:
            return self
        return None

    def start_game(self, game_id):
        self.round_points = 0
        self.last_game_id = game_id
        self.in_game = True
        self.in_queue = False

    def logout(self):
        self.is_online = False
        try:
            time.sleep(0.1)
            self.client_socket.sendall('\0'.encode())
        except ConnectionAbortedError:
            pass
        self.client_socket.shutdown(socket.SHUT_RDWR)
        self.client_socket.close()
        print(f'[Access]: Player {self.username}(#{self.id}) has logged out.')
        self = None
        return None

    def get_input(self, message, valid_chars, max_len, err_msg=None):
        message = message + '\0'
        with self.lock:
            if not isinstance(max_len, int) or max_len > MAX_INPUT_LEN:
                max_len = MAX_INPUT_LEN
            try:
                for i in range(NUM_OF_TRIES):
                    self.client_socket.sendall(message.encode())
                    self.client_socket.settimeout(KICK_TIME)
                    reply_time = time.time()
                    try:
                        inp = self.client_socket.recv(SIZE_OF_DATA).decode().lower()
                    except socket.timeout:
                        self.client_socket.sendall('\nYou type too slowly. '
                                                   'You have been kicked out of the server :c\0'.encode())
                        self.logout()
                        return None
                    reply_time = time.time() - reply_time

                    if reply_time > IGNORE_TIME:
                        return None

                    valid = True
                    if len(inp) > max_len:
                        valid = False
                        self.client_socket.sendall(f'Your input is too long! '
                                                   f'Maximum supported length is {max_len}.\0'.encode())
                        continue
                    if inp is None:
                        valid = False
                    else:
                        for letter in inp:
                            if letter not in valid_chars:
                                self.client_socket.sendall(f'Char "{letter}" is not valid. Try again.\0'.encode())
                                valid = False
                                continue
                    if valid:
                        break
                if valid:
                    return inp
                if err_msg is not None:
                    err_msg = err_msg + '\0'
                    self.client_socket.sendall(err_msg.encode())
                return None
            except ConnectionAbortedError:
                self.logout()
                return None
            except:
                return None

    def get_hashed_password(self, message, max_len):
        password = self.get_input(message, ALPHABET, max_len)  # TODO: secure password measures can be implemented here
        if password is None:
            return None
        return binascii.hexlify(hashlib.pbkdf2_hmac(HASH_METHOD, password.encode(), SALT, ITERATIONS)).decode()

    # adds provided data to a database and returns a Player object
    def register(self):
        args = {'user_id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                'username': f'TEXT({USERNAME_MAX_LEN}) NOT NULL',
                'password': f'TEXT({PASSWORD_MAX_LEN}) NOT NULL',
                'score': 'INTEGER DEFAULT 0',
                'last_game_id': 'INTEGER DEFAULT -1'}

        tables.create_table(LOGIN_REGISTER_TABLE, args)
        username = None
        while username is None:
            username = self.get_input('Choose a unique username: ', ALPHABET + DIGITS, USERNAME_MAX_LEN)
            if tables.is_in_table(LOGIN_REGISTER_TABLE, {'username': username}) is not None:
                self.client_socket.sendall('Username already taken. Try again.\0'.encode())
                username = None
        self.username = username

        while True:
            passwd = self.get_hashed_password('Choose password: ', PASSWORD_MAX_LEN)
            retype_passwd = self.get_hashed_password('Retype the password: ', PASSWORD_MAX_LEN)
            if passwd == retype_passwd:
                break
            self.client_socket.sendall('Passwords not matching. Try again.\0'.encode())
        self.password = passwd

        tables.add_to_table(LOGIN_REGISTER_TABLE, {'username': username, 'password': passwd})
        self.is_online = True
        print(f'[Access]: Player {self.username}(#{self.id}) has registered')
        return self.update_data()

    def is_login_successful(self, table_name, username, passwd):
        if tables.is_in_table(table_name, {'username': username, 'password': passwd}, 'username, password'):
            return True
        self.client_socket.sendall('\nCredentials not matching.\0'.encode())
        return False

    def login(self):
        username = self.get_input('Username: ', ALPHABET + DIGITS, USERNAME_MAX_LEN)
        if username is None:
            return None
        passwd = self.get_hashed_password('Password: ', PASSWORD_MAX_LEN)
        if passwd is None:
            return None
        if self.is_login_successful(LOGIN_REGISTER_TABLE, username, passwd):
            self.client_socket.sendall('\n\nLogin successful\0'.encode())
            self.username = username
            self.password = passwd
            self.is_online = True
            self.update_data()
            print(f'[Access]: Player {self.username}(#{self.id}) has logged in')
            return self
        self.client_socket.sendall('Access denied\0'.encode())
        time.sleep(0.1)
        self.logout()
        return None


class Game:

    def __init__(self, players=None, _id=None):
        self.word = None
        self.lock = Lock()
        self.display_word = None
        self.recent_guess = None
        self.wrong_letters = []
        self.guessed_letters = []
        self.players = players
        self.id = _id
        self.is_running = False
        self.options = {'+': self.guess_letter,
                        '=': self.guess_word}
        tables.create_table(GAME_HISTORY_TABLE, {'game_id': 'INTEGER PRIMARY KEY',
                                                 'selected_word': 'TEXT',
                                                 'num_of_players': 'INTEGER',
                                                 'players_guessing_id': 'TEXT',
                                                 'player_choosing_id': 'INTEGER'})

    def set_word(self, player):
        player.client_socket.sendall('\n[#] Choose a word for this game\0'.encode())
        word = player.get_input('Select a word: ', ALPHABET, MAX_INPUT_LEN,
                                'You have reached maximum number of tries. Another player will select '
                                'the word for this round.')
        if word is not None:
            with open(DICT_PATH) as dict_, mmap.mmap(dict_.fileno(), 0, access=mmap.ACCESS_READ) as dict_content:
                if dict_content.find(word.lower().encode('ascii')) != -1:
                    self.word = word.lower()
                    self.display_word = ''
                    for letter in self.word:
                        if letter in LETTERS_1LINE:
                            self.display_word += '1 '
                        elif letter in LETTERS_2LINE:
                            self.display_word += '2 '
                        elif letter in LETTERS_3LINE:
                            self.display_word += '3 '
                        elif letter in LETTERS_4LINE:
                            self.display_word += '4 '
                        else:
                            player.client_socket.sendall(f'Character {letter} not recognised. '
                                                         f'You have been kicked from the server.')
                            player.logout()
                            raise ValueError(f'Character {letter} not recognised.')
                            return False
                else:
                    player.client_socket.sendall(f'Word {word} is not recognised. '
                                                 f'You have been kicked from the server.')
                    player.logout()
                    print(f'\nWord "{word.lower()}" is not recognised.')
                    return False
            print(f'[Game #{self.id}]: The word "{self.word}" has been chosen by '
                  f'player {player.username}(#{player.id}) for this round.')
            return True
        return False

    def update_display_word_and_recent_guess(self):
        for i in range(len(self.word)):
            if self.display_word[i*2] in '1234' and self.word[i] in self.guessed_letters:
                self.display_word = self.display_word[:i*2] + self.word[i] + self.display_word[i*2+1:]
                self.recent_guess = self.recent_guess[:i*2] + '1' + self.recent_guess[i*2+1:]

    def send_to_all(self, players, message):
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

    def guess_letter(self, player):
        letter = player.get_input('[@] Guess the letter: ', ALPHABET, 1,
                                  'You have reached maximum number of tries. No action will be performed.')
        self.recent_guess = '0 ' * len(self.word)

        if letter is not None:
            letter = letter.lower()
            self.send_to_all(self.players, f'Player {player.username} chose letter "{letter}"')
            if letter in self.word:
                self.guessed_letters.append(letter)
                points = self.word.count(letter) * GUESS_LETTER_POINTS
                player.add_points(points)
                self.update_display_word_and_recent_guess()
                if not re.search('[1-4]+', self.display_word):
                    self.send_to_all(self.players, 'All letters has been guessed!')
                    self.is_running = False
                self.send_to_all(player, '[=] Good guess!')
                return True
            self.wrong_letters.append(letter)
        self.send_to_all(player, '[!] Wrong guess!')
        return False

    def guess_word(self, player):
        word = player.get_input('[@] Guess the word: ', ALPHABET, MAX_INPUT_LEN,
                                'You did not follow the supported format. Your try is over.')
        if word is None:
            return False
        self.send_to_all(self.players, f'Player {player.username} is trying to guess the word')
        if word.lower() == self.word:
            self.display_word = self.word.replace('', ' ')
            player.add_points(GUESS_WORD_POINTS)
            self.send_to_all(self.players, f'\nPlayer {player.username} has guessed the word "{word}"!')
            self.is_running = False
            self.send_to_all(player, '[=] Good guess!')
            return True
        self.send_to_all(player, '[!] Wrong guess')
        self.send_to_all(self.players, f'\nPlayer {player.username} did not guess the word. The round continues!')
        return False

    def get_option(self, player):
        self.send_to_all(player, '\nChoose option:\n'
                                 '\t[+] - guess letter\n'
                                 '\t[=] - guess word\n')
        return player.get_input(f'>> ', self.options.keys(), 1,
                                'You have reached the maximum number of tries and will perform no action.')

    def perform_option(self, player, option):
        try:
            return self.options[option](player)
        except KeyError:
            return False

    def print_and_update_scores(self):
        self.send_to_all(self.players, 'The game has finished.\n\nScores:')
        for player in self.players:
            self.send_to_all(self.players, f'Player: {player.username}\tScore: {player.round_points}')
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
                                                               'player_choosing_id': '[NOT SET]',
                                                               'selected_word': '[NOT SET]'})
            print(f'[Game #{self.id}]: Game has been added to the history')

    def update_history(self, guessing_players_ids, choosing_player_id):
        with self.lock:
            tables.update_table(GAME_HISTORY_TABLE, {'selected_word': self.word,
                                                     'players_guessing_id':
                                                         '\n'.join([str(id_) for id_ in guessing_players_ids]),
                                                     'player_choosing_id': str(choosing_player_id)},
                                f'game_id={self.id}')
            print(f'[Game #{self.id}]: Data has been updated')

    def reset_game_values(self):
        self.word = None
        self.display_word = None
        self.recent_guess = None
        self.wrong_letters = []
        self.guessed_letters = []
        self.is_running = False
        for player in self.players:
            player.in_game = False

    def run_game(self):
        self.initialize_the_game()
        guessing_players = [p.id for p in self.players]
        choosing_player = None
        for player in self.players:
            self.send_to_all(self.players, f'\nPlayer {player.username} '
                                           f'has been selected to choose the word for this round.')
            if self.set_word(player):
                choosing_player = player.id
                guessing_players.remove(choosing_player)
                self.send_to_all(player, f'You have chosen the word "{self.word}" '
                                         f'and are now in the spectator mode.')
                break
        if self.word is None:
            self.send_to_all(self.players, 'Nobody chose the word. The game has been aborted.')
            self.print_and_update_scores()
            self.reset_game_values()
        else:
            self.update_history(guessing_players, choosing_player)
            while self.is_running:
                for player in self.players:
                    if player.id == choosing_player:
                        if not player.is_online:
                            self.send_to_all(self.players, f'Choosing player {player.username} is not in the game.')
                        continue
                    if len(guessing_players) < 1:
                        self.send_to_all(self.players, 'There are not enough players to continue this game. '
                                                       'The game will finish now.')
                        self.is_running = False
                        break
                    if player.id not in guessing_players:
                        break
                    self.send_to_all(self.players, self.display_word)
                    for i in range(MAX_GUESSES):
                        if not player.is_online:
                            try:
                                guessing_players.remove(player.id)
                                self.send_to_all(self.players, f'Guessing player {player.username} has left the game.')
                            except ValueError:
                                pass
                            break
                        if not self.is_running:
                            break
                        opt = self.get_option(player)
                        if opt is not None:
                            if not self.perform_option(player, opt):
                                break
                        self.send_to_all(self.players, self.display_word)
                        if self.recent_guess is not None:
                            self.send_to_all(self.players, f'{self.recent_guess} <- Result of '
                                                           f'player {player.username}\'s try')
                            self.recent_guess = None
                    self.send_to_all(self.players, f'This was player {player.username}\'s last try.')
            self.print_and_update_scores()
            self.reset_game_values()
