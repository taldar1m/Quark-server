from network import *

if not os.path.isfile(db_path):
    open(db_path, 'w').write('')

if not os.path.isfile(chats_db_path):
    open(chats_db_path, 'w').write('')
    conn = sqlite3.connect(chats_db_path)
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE IF NOT EXISTS chats (id real, key text)')

    conn.commit()
    conn.close()

if not os.path.isfile(pkey_path):
    open(pkey_path, 'wb').write(export_private_key(generate_private_key()))

private = import_private_key(pkey_path)
public = export_public_key(get_public_key(private))


def register_user(login, password):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT password FROM users WHERE login = ?', (login,))
    if cursor.rowcount == 1:
        return False
    cursor.execute('INSERT INTO users VALUES (?, ?)', (login, password))
    conn.commit()
    conn.close()
    return True


def process_connection(client_socket):
    client_socket.send(public)
    client_key = import_public_key(client_socket.recv(3072))
    client_socket.send(encrypt(b'Connection OK', client_key))
    login_data = list(decrypt(client_socket.recv(2048), private).split())
    if len(login_data) == 3:
        reg, login, password = login_data
        reg, login, password = reg.decode(), login.decode(), password.decode()
        if reg == reg_code:
            register_user(login, password)
            client_socket.send(pickle.dumps([encrypt(b'Login successful!', client_key)]))
        else:
            client_socket.send(pickle.dumps([encrypt(b'Reg code incorrect!', client_key)]))
            return
    if not check_login(login, password):
        client_socket.close()
        return
    client = Client(client_socket, login, password, server, client_key)
    client.listen_for_client()


conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('CREATE TABLE IF NOT EXISTS users (login text, password text)')
conn.commit()
conn.close()

conn = sqlite3.connect(chats_db_path)
cursor = conn.cursor()

cursor.execute('SELECT * FROM chats')
room_list = cursor.fetchall()
conn.commit()
conn.close()
for room in room_list:
    start_room(room[0], room[1])

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((host, port))
s.listen()

while True:
    client_socket, addr = s.accept()
    Thread(target=process_connection, args=(client_socket,), daemon=True).start()
