# By Tonglong Song 2022/6/8 17:57
import paramiko
from scp import SCPClient
from my_utils import gettime, dt_connect
import os
import timeit
import time
from PIL import Image


def postimg():
    c = dt_connect()
    lastpost = 0
    while True:
        t = gettime()-10
        if lastpost != t:
            if True:
                fname = f"3dpose/frames/{t}.jpg"
                if os.path.exists(fname):
                    try:
                        start = timeit.default_timer()
                        image = Image.open(fname)
                        image.save(fname, quality=70, optimize=True)
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