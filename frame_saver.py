import cv2
import time
from utils import gettime, clean_history

cap = cv2.VideoCapture(0)

while True:
    try:
        ret, frame = cap.read()
        cv2.imwrite('frames/%d.jpg' % gettime(), frame)
    except Exception as e:
        print(e)
        time.sleep(2)
    if gettime() % 1000 == 0:
        clean_history(300, 'frames')
        print('history cleaned')
        time.sleep(0.5)




