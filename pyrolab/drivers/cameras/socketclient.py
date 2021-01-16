import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('10.32.112.199', 2222))

full_msg = ''
while True:
    msg = s.recv(8)
    if len(msg) <= 0:
        break
    full_msg += msg.decode("utf-8")

print(full_msg)