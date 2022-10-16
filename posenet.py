import json
import os.path as osp
import numpy as np
import cv2
import torch
import torchvision.transforms as transforms
from torch.nn.parallel.data_parallel import DataParallel
import torch.backends.cudnn as cudnn

from posenet.main.config import cfg
from posenet.main.model import get_pose_net
from posenet.data.dataset import generate_patch_image
from posenet.common.utils.pose_utils import process_bbox, pixel2cam
from posenet.common.utils.vis import vis_keypoints, vis_3d_multiple_skeleton
from datetime import datetime
import utm


def timestring():
    now = datetime.now()
    return now.strftime("%Y-%m-%d'T'%H:%M:%SZZZZ")


def cordtransfer(origin, x, y):
    utmcoord = utm.project(origin)
    return utm.unproject(utmcoord[0], utmcoord[1], utmcoord[2] + x / 1000, utmcoord[3] + y / 1000)


def print_json(keypoints):
    skeletons = [[0, 16], [16, 1], [1, 15], [15, 14], [14, 8], [14, 11], [8, 9], [9, 10], [10, 19], [11, 12], [12, 13],
                 [13, 20], [1, 2], [2, 3], [3, 4], [4, 17], [1, 5], [5, 6], [6, 7], [7, 18]]
    pload = {'time': timestring()}
    for l in range(len(keypoints)):
        point = {}
        skeleton = {}
        for j in range(len(keypoints[l])):
            point['%d' % j] = ['%.8f' % float(l) for l in list(keypoints[l][j][:3])]
        for k in range(len(skeletons)):
            skeleton['%d' % k] = str(list(skeletons[k]))
        pload['human%d' % l] = {'coordinates': point, 'skeletons': skeleton}
    return json.dumps(pload)


def coordtransform(pose3d, Rvec, Tvec):
    out = np.ones_like(pose3d)
    out = out.astype(np.float64)
    origin = (144.965170, -37.800424)
    for i in range(len(pose3d)):
        for j in range(len(pose3d[i])):
            joint = pose3d[i][j]
            mat = np.matrix(np.array([[joint[0]], [joint[1]], [joint[2]]], dtype=np.float32))
            new = Rvec ** -1 * (mat - Tvec)
            new = new.transpose().A1
            lon, lat = cordtransfer(origin, new[0], new[1])
            out[i][j] = [lon, lat, new[2]/1000]
    return out


def load_posenet_data():
    # argument parsing
    cfg.set_args('0')
    cudnn.benchmark = True

    joint_num = 21

    # snapshot load
    model_path = './snapshot_%d.pth.tar' % int(24)
    assert osp.exists(model_path), 'Cannot find model at ' + model_path
    print('Load checkpoint from {}'.format(model_path))
    model = get_pose_net(cfg, False, joint_num)
    model = DataParallel(model).cuda()
    ckpt = torch.load(model_path)
    model.load_state_dict(ckpt['network'])
    model.eval()
    print('posenet model loaded')
    return model


def human_3d_detection(bbox, depth_list, focal, original_img, model, R, T):
    # MuCo joint set
    joint_num = 21
    joints_name = (
        'Head_top', 'Thorax', 'R_Shoulder', 'R_Elbow', 'R_Wrist', 'L_Shoulder', 'L_Elbow', 'L_Wrist', 'R_Hip', 'R_Knee',
        'R_Ankle', 'L_Hip', 'L_Knee', 'L_Ankle', 'Pelvis', 'Spine', 'Head', 'R_Hand', 'L_Hand', 'R_Toe', 'L_Toe')
    flip_pairs = ((2, 5), (3, 6), (4, 7), (8, 11), (9, 12), (10, 13), (17, 18), (19, 20))
    skeleton = (
        (0, 16), (16, 1), (1, 15), (15, 14), (14, 8), (14, 11), (8, 9), (9, 10), (10, 19), (11, 12), (12, 13), (13, 20),
        (1, 2), (2, 3), (3, 4), (4, 17), (1, 5), (5, 6), (6, 7), (7, 18))

    # prepare input image
    transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize(mean=cfg.pixel_mean, std=cfg.pixel_std)])
    original_img_height, original_img_width = original_img.shape[:2]

    # prepare bbox
    bbox_list = bbox  # xmin, ymin, width, height
    root_depth_list = depth_list  # obtain this from RootNet (https://github.com/mks0601/3DMPPE_ROOTNET_RELEASE/tree/master/demo)
    assert len(bbox_list) == len(root_depth_list)
    person_num = len(bbox_list)

    # normalized camera intrinsics
    princpt = [original_img_width / 2, original_img_height / 2]  # x-axis, y-axis


    # for each cropped and resized human image, forward it to PoseNet
    output_pose_2d_list = []
    output_pose_3d_list = []
    for n in range(person_num):
        bbox = process_bbox(np.array(bbox_list[n]), original_img_width, original_img_height)
        img, img2bb_trans = generate_patch_image(original_img, bbox, False, 1.0, 0.0, False)
        img = transform(img).cuda()[None, :, :, :]

        # forward
        with torch.no_grad():
            pose_3d = model(img)  # x,y: pixel, z: root-relative depth (mm)

        # inverse affine transform (restore the crop and resize)
        pose_3d = pose_3d[0].cpu().numpy()
        pose_3d[:, 0] = pose_3d[:, 0] / cfg.output_shape[1] * cfg.input_shape[1]
        pose_3d[:, 1] = pose_3d[:, 1] / cfg.output_shape[0] * cfg.input_shape[0]
        pose_3d_xy1 = np.concatenate((pose_3d[:, :2], np.ones_like(pose_3d[:, :1])), 1)
        img2bb_trans_001 = np.concatenate((img2bb_trans, np.array([0, 0, 1]).reshape(1, 3)))
        pose_3d[:, :2] = np.dot(np.linalg.inv(img2bb_trans_001), pose_3d_xy1.transpose(1, 0)).transpose(1, 0)[:, :2]
        output_pose_2d_list.append(pose_3d[:, :2].copy())

        # root-relative discretized depth -> absolute continuous depth
        pose_3d[:, 2] = (pose_3d[:, 2] / cfg.depth_dim * 2 - 1) * (cfg.bbox_3d_shape[0] / 2) + root_depth_list[n]
        pose_3d = pixel2cam(pose_3d, focal, princpt)
        output_pose_3d_list.append(pose_3d.copy())

    # visualize 3d poses
    Rvec = np.matrix(R)
    Tvec = np.matrix(T)
    vis_kps = np.array(output_pose_3d_list)
    vis_kps = coordtransform(vis_kps, Rvec, Tvec)
    return print_json(vis_kps)

    # vis_3d_multiple_skeleton(vis_kps, np.ones_like(vis_kps), skeleton, vis_img, file_name)
