# This isn't the main repository!! Go to https://github.com/taldar1m/Quark
## How does this work?
Clients communicate with each other through the server using RSA encrypted sockets with unique keys on the client side. So, server knows your username, but all messages are encrypted from client to client with AES-GCM and server can not read them. To register on server you need to get authentification code from admin(see it in config as reg_code).

## Getting started
### How to deploy a server?
```
git clone https://github.com/taldar1m/Quark-server && cd Quark-server && pip install cryptography
```
Then edit the config and run MainService.py. Now you can share your registration code with others.
