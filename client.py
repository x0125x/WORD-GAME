import socket
import signal
import mmap
from random import randint
import re
import sys
from time import sleep


HOST = '127.0.0.1'
PORT = 65432
SIZE_OF_DATA = 1024
MAX_TRIES = 3

DICT_PATH = 'static/resources/slowa.txt'

LETTERS_1LINE = 'weęruioóaąsśzżźxcćvnńm'
LETTERS_2LINE = 'pyjgq'
LETTERS_3LINE = 'tlłbdhk'
LETTERS_4LINE = 'f'


def build_dict(file_path):
    file = open(file_path, mode='r', encoding='utf8')
    mapped_file = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
    dictionary = {}
    line_content = mapped_file.readline().decode()
    line_num = 0
    while line_content:
        dictionary[line_num] = line_content
        dictionary[line_num] = line_content
        line_content = mapped_file.readline().decode()[:-2]
        line_num += 1
    return dictionary


DICT = build_dict(DICT_PATH)
DICT_LEN = len(DICT)


class Connection:
    def __init__(self):
        self.server_IP = HOST
        self.server_port = PORT
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn_alive = False
        signal.signal(signal.SIGINT, self.signal_handler)
        self.word = None
        self.guessed = ''
        self.word_list = []

    def connect(self):
        print('Press CTRL-C to exit.\n')
        try:
            self.client.connect((self.server_IP, self.server_port))
            self.conn_alive = True
            self.client.sendall(f'{LOGIN}\n{PASSWORD}\0'.encode())
            data = self.receive()
            if data == '+1':
                print('You have logged in successfully\n'
                      'Used encoding set number: 1')
                print('\nWaiting for the game to start...\n')
            elif data == '-':
                print('Access denied. Quitting...')
                self.disconnect()
                return 0
            # waiting in the queue
            while self.conn_alive:
                self.client.settimeout(0.2)
                try:
                    data = self.receive()
                    if data:
                        print(data)
                        break
                except socket.timeout:
                    pass
            # the game has started
            while self.conn_alive:
                if data:
                    data = self.send(data)
                data = self.receive_and_display()
                if not self.conn_alive:
                    return 0
                print(f'Current word state: {self.word}')
        except socket.error:
            pass

    def signal_handler(self, sig, frame):
        self.disconnect()
        exit(0)

    def disconnect(self):
        print('Disconnecting...')
        self.conn_alive = False

    def receive(self):
        return self.client.recv(SIZE_OF_DATA).decode().replace('\n', '\0').replace('\0', '')

    def receive_and_display(self):
        data = self.client.recv(SIZE_OF_DATA).decode().replace('\0', '\n')[:-1]
        print(f'Received: {data}')
        return data

    @staticmethod
    def get_word():
        line_num = randint(0, len(DICT))
        print(f'Choosing word: {DICT[line_num]}')
        return DICT[line_num] + '\0'

    def is_guess_matching(self, guess):
        for i in range(len(self.word)):
            if self.word[i] == '1' and not guess[i] in LETTERS_1LINE:
                return False
            elif self.word[i] == '2' and not guess[i] in LETTERS_2LINE:
                return False
            elif self.word[i] == '3' and not guess[i] in LETTERS_3LINE:
                return False
            elif self.word[i] == '4' and not guess[i] in LETTERS_4LINE:
                return False
        return True

    def get_word_list(self):
        word_list = []
        for i in range(len(DICT)):
            word = DICT[i]
            if len(self.word) == len(word) and self.is_guess_matching(word):
                word_list.append(word)
        return word_list

    def find_word(self):
        if len(self.word_list) > 10:
            return None
        pattern = re.compile(re.sub(r'(\d)', '.', self.word))
        for word in self.word_list:
            if pattern.match(word) and self.is_guess_matching(word):
                self.word_list.remove(word)
                return '=' + word + '\0'
        return None

    def get_unique(self, letter_group):
        for letter in letter_group:
            if letter not in self.guessed:
                return letter
        return None

    def get_letter(self):
        if re.search('1', self.word):
            letter = self.get_unique(LETTERS_1LINE)
            if letter is not None:
                self.guessed += letter
                return '+' + letter + '\0'
        if re.search('2', self.word):
            letter = self.get_unique(LETTERS_2LINE)
            if letter is not None:
                self.guessed += letter
                return '+' + letter + '\0'
        if re.search('3', self.word):
            letter = self.get_unique(LETTERS_3LINE)
            if letter is not None:
                self.guessed += letter
                return '+' + letter + '\0'
        if re.search('4', self.word):
            letter = self.get_unique(LETTERS_4LINE)
            if letter is not None:
                self.guessed += letter
                return '+' + letter + '\0'
        return None

    def update_word(self, guess_result):
        for i in range(len(self.word)):
            if guess_result[i] == '1':
                self.word = self.word[:i] + self.guessed[-1] + self.word[i+1:]
        print(f'The word has been updated to: {self.word}')

    def send(self, data_last):
        try:
            data = None
            if data_last[-1] == '?':
                if data_last[0] == '=':
                    score = data_last.replace('\n', '\0').split('\0')[1]
                    print(f'YOUR SCORE IS: {score}')
                self.disconnect()
                return 0
            elif data_last[0] == '@':
                data = self.get_word()
                self.word = data
                self.client.sendall(data.encode())
                self.disconnect()
                return 0
            elif re.match(r'[1-4]+', data_last):
                self.word = data_last
                self.word_list = self.get_word_list()
                data = self.get_letter()
            elif re.match(r'[0-1]+', data_last):
                self.word = data_last
                data = self.get_letter()
            elif data_last[0] == '#':
                data = self.get_letter()
            elif data_last[0] == '=':
                data_last = data_last.replace('\0', '\n').split('\n')[1]
                if data_last is not None:
                    self.update_word(data_last)
                data = self.find_word()
                if data is None:
                    data = self.get_letter()
            elif data_last[0] == '!':
                data = self.find_word()
                if data is None:
                    data = self.get_letter()
            if data is not None:
                print(f'Sending data: {data}')
                self.client.sendall(data.encode())
        except socket.error:
            print(f'Error while sending data: {socket.error}')


if __name__ == '__main__':
    if len(sys.argv) == 3:
        LOGIN = sys.argv[1]
        PASSWORD = sys.argv[2]
    else:
        print(f'FOLLOW GIVEN SYNTAX: python3 client.py <username> <password>')

    for i in range(MAX_TRIES):
        c = Connection()
        c.connect()
        sleep(5)
