# By Tonglong Song 2022/6/8 17:57
import paramiko
from scp import SCPClient
from utils import gettime
import os
import timeit
import time
from PIL import Image


            



def dt_connect():
    k = paramiko.RSAKey.from_private_key_file("3dpose/app1server.pem")
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
            if True:
                if os.path.exists(f"3dpose/frames/{t}.jpg"):
                    try:
                        start = timeit.default_timer()
                        img = Image.open(f"3dpose/frames/{t}.jpg")
                        img.save(f"3dpose/frames/{t}.jpg", optimize=True, quality = 50)
                        with SCPClient(c.get_transport()) as scp:
                            scp.put(f"3dpose/frames/{t}.jpg", '/home/ubuntu/posecapture/tempdata/cam0/')
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

time.sleep(5)
postimg()