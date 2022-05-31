import socket
import os
from argparse import ArgumentParser
from utils import clean_history

def frame_receiver(args):
    # device's IP address
    # the ip address or hostname of the server, the receiver
    host = args.server_ip
    port = 18123
    # the name of file we want to send, make sure it exists
    # get the file size
    # receive 4096 bytes each time
    BUFFER_SIZE = 4096
    SEPARATOR = "<separator>"

    s = socket.socket()
    print(f"[+] Connecting to {host}:{port}")
    s.connect((host, port))
    print("[+] Connected.")

    # receive the file infos
    # receive using client socket, not server socket
    received = s.recv(BUFFER_SIZE).decode()
    filename, filesize = received.split(SEPARATOR)
    # remove absolute path if there is
    filename = os.path.basename(filename)
    # convert to integer
    filesize = int(filesize)

    # start receiving the file from the socket
    # and writing to the file stream
    with open(f"{args.frame_root}/{filename}", "wb") as f:
        while True:
            # read 1024 bytes from the socket (receive)
            bytes_read = s.recv(BUFFER_SIZE)
            if not bytes_read:
                # nothing is received
                # file transmitting is done
                break
            # write to the file the bytes we just received
            f.write(bytes_read)
    print(filename)
    # close the client socket
    s.close()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('frame_root', type=str, help='Where frame will be saved')
    parser.add_argument('server_ip', type=str, help='ip address of the server')
    while True:
        try:
            frame_receiver(parser.parse_args())
            clean_history(30, parser.parse_args())
        except:
            pass
