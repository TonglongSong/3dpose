import socket
import os
import time
from os.path import exists
from requests import get


def gettime():
    t = time.time()
    diff = t - int(t)
    if diff >= 0.5:
        return int(t)*10-5
    else:
        return int(t)*10-10
    
def clean_history(t):
    namelst = os.listdir('frames')
    namelst = [int(i[:-4]) for i in namelst]
    namelst = [i for i in namelst if i < gettime()-t*10]
    for i in namelst:
        os.remove(f"frames/{i}.jpg")
    

separator = '<separator>'
buffer_size = 4096

server_host = '0.0.0.0'
server_port = 8123
ip = get('https://api.ipify.org'). text

s = socket.socket()
s.bind((server_host, server_port))
s.listen(5)                                                                                                                                  
print(f"listening on {ip} port {server_port}")
while True:
    clean_history(30)
    filename = f"frames/{gettime()}.jpg"
    if exists(filename):
        filesize = os.path.getsize(filename)
        client_socket, address = s.accept()
        print(f"connected to {address}")
        client_socket.send(f"{filename}{separator}{filesize}".encode())
        with open(filename, "rb") as f:
            while True:
                bytes_read = f.read(buffer_size)
                if not bytes_read:
                    break
                client_socket.sendall(bytes_read)
        client_socket.close()
    else:
        print('no real time frame detected')
    
    time.sleep(0.5)






s.close