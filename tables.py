import sqlite3
from threading import Lock
from config import DB_FOLDER

lock = Lock()


# takes in table name and
# a dictionary containing column names as keys and desired types of values as values:
# args={col1: val_type1, col2: val_type2, ...}
def create_table(name, args):
    with lock:
        conn = sqlite3.connect(f'{DB_FOLDER}/{name}')
        c = conn.cursor()

        keys = list(args.keys())
        vals = list(args.values())

        query = ''
        for i in range(len(args)):
            query += keys[i] + ' ' + vals[i].upper() + ', '
        query = query[:-2]

        c.execute(f'CREATE TABLE IF NOT  EXISTS {name} ({query})')
        conn.commit()
        conn.close()


# takes in table name and a dictionary containing column names as keys and desired values as values:
# args={col1: val1, col2: val2, ...}
def add_to_table(name, args):
    try:
        with lock:
            conn = sqlite3.connect(f'{DB_FOLDER}/{name}')
            c = conn.cursor()
            keys = list(args.keys())
            vals = tuple(args.values())
            query = f'INSERT INTO {name} ({", ".join(keys)}) VALUES ({", ".join("?" * len(list(vals)))})'
            c.execute(query, vals)
            conn.commit()
            id = c.lastrowid
            conn.close()
            return id
    except sqlite3.OperationalError:
        print(f'[Data]: Error when getting data from table {name}:\n{sqlite3.OperationalError}')
        return None


# takes in table name and a dictionary containing column names as keys and desired values as values:
# args={col1: val1, col2: val2, ...}
def update_table(name, args, condition):
    try:
        with lock:
            conn = sqlite3.connect(f'{DB_FOLDER}/{name}')
            c = conn.cursor()
            keys = list(args.keys())
            vals = tuple(args.values())
            query = f'UPDATE {name} SET {" = ?, ".join(keys) + " = ?"} WHERE {condition}'
            c.execute(query, vals)
            conn.commit()
            conn.close()
    except sqlite3.OperationalError:
        print(f'[Data]: Error when getting data from table {name}:\n{sqlite3.OperationalError}')
        return None


# takes in table name and a 'condition dictionary' containing column names and their values:
# args={col1: val1, col2: val2, ...}, as well as what's being fetched (default = everything)
# and returns fetched info (or None if record not found)
def is_in_table(name, args={}, fetch='*'):
    try:
        with lock:
            conn = sqlite3.connect(f'{DB_FOLDER}/{name}')
            c = conn.cursor()

            keys = list(args.keys())
            vals = [str(arg) for arg in list(args.values())]
            query = ' = ? AND '.join(keys) + ' = ?'

            c.execute(f'SELECT {fetch} FROM {name} WHERE {query}', tuple(vals))
            result = c.fetchone()
            conn.commit()
            conn.close()
            return result
    except sqlite3.OperationalError:
        print(f'[Data]: Error when getting data from table {name}:\n{sqlite3.OperationalError}')
        return None


# takes in table name and a selected list containing column names:
# args={col1, col2, ...}, as well as the condition of ordering
# and returns fetched info
def get_in_order(name, fetch, order):
    try:
        with lock:
            conn = sqlite3.connect(f'{DB_FOLDER}/{name}')
            c = conn.cursor()

            c.execute(f'SELECT {fetch} FROM {name} ORDER BY {order}')
            result = c.fetchall()
            conn.commit()
            conn.close()
            return result
    except sqlite3.OperationalError:
        print(f'[Data]: Error when getting data from table {name}:\n{sqlite3.OperationalError}')
        return None
