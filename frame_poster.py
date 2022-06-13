# By Tonglong Song 2022/6/8 17:57
import paramiko
from scp import SCPClient
from utils import gettime
import os
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


def postimg():
    c = dt_connect()
    lastpost = 0
    while True:
        t = gettime()-10
        if lastpost != t:
            if c.get_transport().is_alive():
                if os.path.exists(f"frames/{t}.jpg"):
                    try:
                        start = timeit.default_timer()
                        with SCPClient(c.get_transport()) as scp:
                            scp.put(f"frames/{t}.jpg", '/home/ubuntu/posecapture/tempdata/cam0/')
                        stop = timeit.default_timer()
                        print(f"{t}.jpg posted in {stop - start} second" )
                        lastpost = t
                    except Exception as e:
                        print(e)
                else:
                    print('no image detected, check camera')
                    time.sleep(1)

            else:
                print("disconnected, trying to reconnect")
                try:
                    c = dt_connect()
                except Exception as e:
                    print(e)
        else:
            time.sleep(0.1)

postimg()