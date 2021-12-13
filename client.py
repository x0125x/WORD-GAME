import socket
import msvcrt
import time
import signal

HOST = '127.0.0.1'
PORT = 65432
SIZE_OF_DATA = 1024
MAX_TRIES = 3


class Connection:
    def __init__(self):
        self.server_IP = HOST
        self.server_port = PORT
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn_alive = False
        signal.signal(signal.SIGINT, self.disconnect)

    def connect(self, tries=MAX_TRIES):
        print('Press CTRL-C to exit.\n')
        time.sleep(1)
        if tries > 0:
            try:
                self.client.connect((self.server_IP, self.server_port))
                self.conn_alive = True
                data = self.client.recv(SIZE_OF_DATA).decode()
                print(data)
                while data:
                    if not self.conn_alive:
                        tries = 0
                        break
                    self.client.settimeout(0.1)
                    try:
                        data = self.client.recv(SIZE_OF_DATA).decode()
                        if data == '\0':
                            self.conn_alive = False
                            continue
                        data = data.split('\0')
                        for d in data:
                            print(d)
                    except socket.timeout:
                        self.send(0.1)
            except socket.error:
                print(f'Error: {socket.error}\nTrying to reconnect...')
                self.connect(tries - 1)

    def disconnect(self, sig, frame):
        print('Disconnecting...')
        self.conn_alive = False

    def get_client_input(self, time_max):
        enter_key = 13
        space_bar_key = 32
        backspace = 8

        reply_time = time.time()
        inp = ''
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getche()
                if ord(char) == enter_key:                                              # enter pressed
                    break
                elif ord(char) >= space_bar_key:                                        # space bar or above in ASCII
                    inp += "".join(map(chr, char))
                elif ord(char) == backspace and len(inp) > 0:                           # backspace pressed
                    inp = inp[:-1]
            if len(inp) == 0 and (time.time() - reply_time) > time_max:
                return None
        return inp

    def send(self, time_max):
        try:
            data = self.get_client_input(time_max)
            if data is not None:
                self.client.sendall(data.encode())
        except socket.error:
            print(f'Error while sending data: {socket.error}')


if __name__ == '__main__':
    c = Connection()
    c.connect()
