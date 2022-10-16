import time
import os
import paramiko


def dt_connect():
    k = paramiko.RSAKey.from_private_key_file("3dpose/app1server.pem")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("connecting")
    c.connect(hostname="45.113.234.32", username="ubuntu", pkey=k)
    print("connected")
    return c


def gettime():
    t = time.time()
    diff = t - int(t)
    if diff >= 0.5:
        return int(t)*10+5
    else:
        return int(t)*10


def clean_history(t, directory):
    namelst = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    namelst = [int(i[:-4]) for i in namelst]
    namelst = [i for i in namelst if i < gettime()-t*10]
    for i in namelst:
        if os.path.exists(f"{directory}/{i}.jpg"):
            os.remove(f"{directory}/{i}.jpg")