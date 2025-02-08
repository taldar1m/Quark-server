import socket, sqlite3, os, datetime
from threading import Thread
from encryption import *
from config import *
import pickle

server = {}


def start_room(id, key):
    global server
    room = ChatRoom(id, key)
    server[id] = room


def create_room(id, key):
    conn = sqlite3.connect(chats_db_path)
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE IF NOT EXISTS chats (id real, key text)')
    cursor.execute('INSERT INTO chats VALUES (?, ?)', (id, key))

    conn.commit()
    conn.close()

    start_room(id, key)


def check_login(user, password):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT password FROM users WHERE login = ?', (user,))
    stored_password = cursor.fetchone()[0]
    if stored_password == password:
        return True
    return False
    conn.close()


class ChatRoom():
    
    def __init__(self, id, key):
        self.id = id
        self.key = key
        self.clients = {}
        self.pkey = import_private_key(pkey_path)
        self.public = export_public_key(get_public_key(self.pkey))

    def process_message(self, message, username, datetime):
        user, data, dtime = username, message, datetime
        for client_key in self.clients:
            client = self.clients[client_key]
            try:
                if datetime != '':
                    dta = pickle.dumps([encrypt(user.encode(), client[1]), data, encrypt(dtime.encode(), client[1])])
                else:
                    dta = pickle.dumps([encrypt(message.encode(), client[1])])
                client[0].send(dta)
            except Exception as e:
                pass
    
    def client_disconnect(self, username):
        self.clients.pop(username)
        self.process_message(f'{username} left the chat', '', '')
    
    def login(self, login, password, key, socket_connection, public_key):
        if check_login(login, password) and key == self.key:
            self.clients[login] = [socket_connection, public_key]
            socket_connection.send(pickle.dumps([encrypt(b'Login successful!', public_key)]))
            Thread(target=self.process_message, args=(f'{login} entered the chat', '', ''), daemon=True).start()
            return True
        socket_connection.send(pickle.dumps([encrypt(b'Login attempt failed. Incorrect password or room key!', public_key)]))
        return False


class Client():

    def __init__(self, socket_connection, login, password, server, public_key):
        self.socket = socket_connection
        self.login = login
        self.password = password
        self.room = None
        self.public = public_key
        self.server = server
        self.private_key = import_private_key(pkey_path)
    
    def connect_to_room(key, room_id):
        self.server[room_id].login(self.login, self.password, key, self.socket, self.public)
        self.room = room_id
    
    def listen_for_client(self):
        while True:
            try:
                message = self.socket.recv(40960)
                if message == b'':
                    self.socket.close()
                try:
                    message = decrypt(message, self.private_key)
                    message = message.decode()
                except:
                    pass
                if message == 'EXIT ROOM':
                    self.server[self.room].client_disconnect(self.login)
                    self.room = None
                    continue
                if 'ENTER ROOM' in str(message):
                    room_id, key = message.split()[2], message.split()[3]
                    try:
                        if not self.server[room_id.encode()].login(self.login, self.password, key, self.socket, self.public):
                            continue
                        if self.room:
                            self.server[self.room].client_disconnect(self.login)
                    except:
                        pass
                    self.room = room_id.encode()
                    continue
                if 'CREATE ROOM' in str(message):
                    room_key = message.split()[2]
                    room_id = hash((self.login + str(datetime.datetime.now())).encode())
                    self.socket.send(encrypt(room_id, self.public))
                    create_room(room_id, room_key)
                if self.room is None:
                    continue
                Thread(target=self.server[self.room].process_message, args=(message, self.login, str(datetime.datetime.now())), daemon=True).start()
            except Exception as e:
                try:
                    self.server[self.room].client_disconnect(self.login)
                except:
                    pass
                self.socket.close()
                return
