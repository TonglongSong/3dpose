# By Tonglong Song 2022/6/8 17:57
import paramiko
from scp import SCPClient
from utils import gettime, clean_history
from argparse import ArgumentParser
import timeit
import time


def dt_connect():
    k = paramiko.RSAKey.from_private_key_file("app1server.pem")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("connecting")
    c.connect(hostname="45.113.234.32", username="ubuntu", pkey=k)
    print("connected")
    return c


def receiveimg(n):
    c = dt_connect()
    lastrec = 0
    while True:
        t = gettime() - 20
        if lastrec != t:
            if c.get_transport().is_alive():
                try:
                    start = timeit.default_timer()
                    for i in range(n):
                        with SCPClient(c.get_transport()) as scp:
                            scp.get(f"/home/ubuntu/posecapture/tempdata/cam{i}/{t}.jpg", f"frames/cam{i}")
                    stop = timeit.default_timer()
                    print(f"{t}.jpg received from {n} cameras in {stop - start} second")
                    lastrec = t
                except Exception as e:
                    print(e)
                    time.sleep(2)
            else:
                print("disconnected, trying to reconnect")
                try:
                    c = dt_connect()
                except Exception as e:
                    print(e)

        elif gettime() % 1000 == 0:
            for i in range(n):
                clean_history(300, f"frames/cam{i}")
            print('history cleaned')
            time.sleep(0.5)
        else:
            time.sleep(0.1)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument(
        '-c', '--camera-numbers', type=int, help='Number of cameras installed')
    args = parser.parse_args()
    receiveimg(args.camera_numbers)