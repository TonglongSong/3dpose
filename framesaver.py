import cv2
import time

def gettime():
    t = time.time()
    diff = t - int(t)
    if diff >= 0.5:
        return int(t)*10+5
    else:
        return int(t)*10

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    cv2.imwrite('frames/%d.jpg' % gettime(), frame)



