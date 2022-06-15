import time
from utils import gettime, clean_history
from picamera import PiCamera
import os
import timeit



if not os.path.exists('3dpose/frames/'):
    os.makedirs('3dpose/frames/')
camera = PiCamera()
camera.resolution = (480, 270)
lastframe = 0
lastclean = 0
while True:
    t = gettime()
    if lastframe != t:
        try:
            start = timeit.default_timer()
            camera.capture(f"3dpose/frames/{t}.jpg")
            stop = timeit.default_timer()
            print(f"{t}.jpg captured in {stop - start} second" )
            lastframe = t
        except Exception as e:
            print(e)
            time.sleep(2)
        if t % 1000 == 0 and t != lastclean:
            clean_history(100, '3dpose/frames')
            print('history cleaned')
            lastclean = t
    else:
        time.sleep(0.01)






