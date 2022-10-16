# By Tonglong Song 2022/6/8 17:57
import paramiko
from scp import SCPClient
from my_utils import gettime, clean_history
from argparse import ArgumentParser
import timeit
import time
import os

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
    endtime = gettime() + 600
    t = 0
    stats = {}
    for i in n:
        stats[f"cam{i}"] = 0
    stats['one_fail'] = 0
    stats['attempts'] = 0
    while t < endtime:
        t = gettime() - 30
        if lastrec != t:
            stats['attempts'] += 1
            start = timeit.default_timer()
            fail_count = 0
            for i in n:
                try:
                    with SCPClient(c.get_transport()) as scp:
                        scp.get(f"/home/ubuntu/posecapture/tempdata/cam{i}/{t}.jpg", f"frames/cam{i}")
                except Exception as e:
                    print(e)
                    stats[f"cam{i}"] += 1
                    fail_count += 1
            if fail_count >= 1:
                stats['one_fail'] += 1
            stop = timeit.default_timer()
            print(f"{t}.jpg received, {fail_count} failed, time = {stop - start} second")
            lastrec = t
        else:
            time.sleep(0.1)
    print(f"analysis finished, total of {stats['attempts']} attempts are made")
    print(f"{stats['one_fail']} attempts have at least one camera failed")
    for i in n:
        print(f"cam{i} failed {stats[f'cam{i}']} times")


if __name__ == '__main__':
    n = [0, 2, 3, 4]
    receiveimg(n)
