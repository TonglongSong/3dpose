# By Tonglong Song 2022/6/8 17:57
import paramiko
from scp import SCPClient
from my_utils import gettime, clean_history, dt_connect
from argparse import ArgumentParser
import timeit
import time
import os


def receiveimg():
    c = dt_connect()
    lastrec = 0
    i = camera
    while True:
        t = gettime() - 20
        if lastrec != t:
            if c.get_transport().is_alive():
                try:
                    with SCPClient(c.get_transport()) as scp:
                        start = timeit.default_timer()
                        scp.get(f"/home/ubuntu/posecapture/tempdata/cam{i}/{t}.jpg", f"frames/cam{i}")
                        stop = timeit.default_timer()
                        print(f"{t}.jpg received from camera{i} in {stop - start} second")
                    lastrec = t
                except Exception as e:
                    if os.path.exists(f"frames/cam{i}/{t}.jpg"):
                        os.remove(f"frames/cam{i}/{t}.jpg")
                    print(e)
                    time.sleep(0.5)
            else:
                print("disconnected, trying to reconnect")
                try:
                    c = dt_connect()
                except Exception as e:
                    print(e)
        else:
            time.sleep(0.1)

        if gettime() % 1000 == 0:
            clean_history(300, f"frames/cam{i}")
            print('history cleaned')
            time.sleep(0.5)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument(
        '-c', '--camera-number', type=int, default="0", help='list of camera id you want to receive image from')
    args = parser.parse_args()
    camera = args.camera_number
    receiveimg()