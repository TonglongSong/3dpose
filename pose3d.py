import time
from rootnet import findrootdepth, load_rootnet_data
from posenet import human_3d_detection, load_posenet_data
from yolo_opencv import get_bbox, load_yolo
import timeit
import paho.mqtt.client as mqtt
import os
import numpy as np
import cv2
from my_utils import gettime
from camera_parameters import get_cam_parameter
from argparse import ArgumentParser



def combined(image, net, classes, rootnet, posenet):
    bbox_list = get_bbox(image, classes, net)
    focal = [args.focal, args.focal]
    depth_list = findrootdepth(bbox_list, focal, image, rootnet)
    pload = human_3d_detection(bbox_list, depth_list, focal, image, posenet, Rvec, Tvec)
    return pload


def undistort(img_path):
    img = cv2.imread(img_path)
    map1, map2 = cv2.fisheye.initUndistortRectifyMap(K, D, np.eye(3), K, DIM, cv2.CV_16SC2)
    undistorted_img = cv2.remap(img, map1, map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    return undistorted_img


def pose3d(net, classes, rootnet, posenet):
    lastimg = 0
    while True:
        t = gettime() - 30
        if lastimg != t:
            img_path = f"frames/cam{args.camera}/{t}.jpg"
            if os.path.exists(img_path):
                start = timeit.default_timer()
                image = undistort(img_path)
                pload = combined(image, net, classes, rootnet, posenet)
                client.publish(topicstr, payload=pload, qos=0, retain=False)
                stop = timeit.default_timer()
                print(pload)
                print(f"skeleton {t} published in {stop - start} second")
                lastimg = t
            else:
                print(f'waiting for image {t}')
                time.sleep(1)
        else:
            time.sleep(0.1)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        '--camera', type=int, default=0, help='which camera parameter to be used')
    parser.add_argument(
        '--focal', type=int, default=900, help='focal length')
    args = parser.parse_args()

    host = 'mqtt.digitwin.com.au'  # fill in the IP of your gateway

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("connected OK Returned code=", rc)
        else:
            print("Bad connection Returned code=", rc)


    # callback triggered by a new Pozyx data packet
    def on_publish(client, userdata, msg):
        print('msg published')


    # set client
    client = mqtt.Client(client_id='Pozyx-tag-positions')
    # set callbacks
    client.on_connect = on_connect
    client.on_publish = on_publish
    # set credentials
    client.username_pw_set('csdila-3dpose-publisher', password='ux693dD3x')
    # set certificate
    client.tls_set('isrgrootx1.pem')
    client.connect(host, port=8883)
    client.loop_start()
    #topic
    topicstr = 'uom/parkville/melbourneconnect/level6/csdila/3dpose/humanSkeleton'

    # load trained model
    rootnet_model = load_rootnet_data()
    posenet_model = load_posenet_data()
    classes, net = load_yolo()

    # load camera parameters
    DIM = (1920, 1080)
    K, D, Rvec, Tvec = get_cam_parameter(args.camera)
    # start loop
    pose3d(net, classes, rootnet_model, posenet_model)



