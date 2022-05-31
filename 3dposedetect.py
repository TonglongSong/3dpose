# Copyright (c) OpenMMLab. All rights reserved.
import json
import os
import os.path as osp
from argparse import ArgumentParser
import time

import cv2
import mmcv
import numpy as np
import torch
from mmcv import Config
from mmcv.parallel import collate, scatter

from mmpose.apis.inference import init_pose_model
from mmpose.core.post_processing import get_affine_transform
from mmpose.datasets.dataset_info import DatasetInfo
from mmpose.datasets.pipelines import Compose

from utils import gettime
from datetime import datetime
import requests
from tqdm import tqdm


def download(url: str, fname: str):
    resp = requests.get(url, stream=True)
    total = int(resp.headers.get('content-length', 0))
    # Can also replace 'file' with a io.BytesIO object
    with open(fname, 'wb') as file, tqdm(
        desc=fname,
        total=total,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in resp.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)


def timestring():
    now = datetime.now()
    return now.strftime("%Y-%m-%d'T'%H:%M:%SZZZZ")


def get_scale(target_size, raw_image_size):
    w, h = raw_image_size
    w_resized, h_resized = target_size
    if w / w_resized < h / h_resized:
        w_pad = h / h_resized * w_resized
        h_pad = h
    else:
        w_pad = w
        h_pad = w / w_resized * h_resized

    scale = np.array([w_pad, h_pad], dtype=np.float32)

    return scale


def get_panoptic_camera_parameters(cam_file,
                                   camera_names,
                                   M=[[1.0, 0.0, 0.0], [0.0, 0.0, -1.0],
                                      [0.0, 1.0, 0.0]]):
    with open(cam_file) as cfile:
        calib = json.load(cfile)

    M = np.array(M)
    cameras = {}
    for cam in calib['cameras']:
        if cam['name'] in camera_names:
            sel_cam = {}
            R_w2c = np.array(cam['R']).dot(M)
            T_w2c = np.array(cam['t']).reshape((3, 1)) * 10.0  # cm to mm
            R_c2w = R_w2c.T
            T_c2w = -R_w2c.T @ T_w2c
            sel_cam['R'] = R_c2w.tolist()
            sel_cam['T'] = T_c2w.tolist()
            sel_cam['K'] = cam['K'][:2]
            distCoef = cam['distCoef']
            sel_cam['k'] = [distCoef[0], distCoef[1], distCoef[4]]
            sel_cam['p'] = [distCoef[2], distCoef[3]]
            cameras[cam['name']] = sel_cam

    assert len(cameras) == len(camera_names)

    return cameras


def get_input_data(img_path, cam_file, t):
    exist = True
    camera_names = sorted(
        [d for d in os.listdir(img_path) if osp.isdir(osp.join(img_path, d))])
    directories = [osp.join(img_path, d) for d in camera_names]
    num_cameras = len(camera_names)
    # load camera parameters
    cameras = get_panoptic_camera_parameters(cam_file, camera_names)
    input_data = []
    for i in range(num_cameras):
        single_view_camera = cameras[camera_names[i]].copy()
        image_file = osp.join(directories[i], f"{t}.jpg")
        if not osp.exists(image_file):
            exist = False
        input_data.append({
            'image_file': image_file,
            'camera': single_view_camera,
            'sample_id': i,
        })

    return input_data, num_cameras, exist

def print_json(input,
                    img,
                    img_metas,
                    input_heatmaps=None,
                    dataset_info=None,
                    out_dir=None
               ):
    """Visualize the results."""
    result = input.forward_test(
        img, img_metas, input_heatmaps=input_heatmaps)
    pose_3d = result['pose_3d']
    batch_size = pose_3d.shape[0]
    # get kpts and skeleton structure

    for i in range(batch_size):

        pose_3d_i = pose_3d[i]
        pose_3d_i = pose_3d_i[pose_3d_i[:, 0, 3] >= 0]

        num_persons, num_keypoints, _ = pose_3d_i.shape
        pose_3d_list = [p[..., [0, 1, 2, 4]]
                        for p in pose_3d_i] if num_persons > 0 else []
        skeletons = dataset_info.skeleton
        pload = {'time': timestring()}
        for l in range(len(pose_3d_list)):
            point = {}
            skeleton = {}
            for j in range(len(pose_3d_list[l])):
                point['%d' % j] = ['%.6f' % float(l) for l in list(pose_3d_list[l][j][:3])]
            for k in range(len(skeletons)):
                skeleton['%d' % k] = str(list(skeletons[k]))
            pload['human%d' % l] = {'coordinates': point, 'skeletons': skeleton}

        print(json.dumps(pload))





def inference(args):
    config_dict = Config.fromfile('voxelpose_prn64x64x64_cpn80x80x20_panoptic_cam5.py')
    cfg = Config.fromfile('panoptic_body3d.py')
    dataset_info = cfg._cfg_dict['dataset_info']
    dataset_info = DatasetInfo(dataset_info)

    model = init_pose_model(
        config_dict, 'voxelpose_prn64x64x64_cpn80x80x20_panoptic_cam5-545c150e_20211103.pth', device=args.device.lower())
    pipeline = [
        dict(
            type='MultiItemProcess',
            pipeline=[
                dict(type='ToTensor'),
                dict(
                    type='NormalizeTensor',
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]),
            ]),
        dict(type='DiscardDuplicatedItems', keys_list=['sample_id']),
        dict(
            type='Collect',
            keys=['img'],
            meta_keys=['sample_id', 'camera', 'center', 'scale',
                       'image_file']),
    ]
    pipeline = Compose(pipeline)

    while True:
        input_data, num_cameras, exist = get_input_data('frames/',
                                                 'frames/camera_parameters.json', gettime()-30)
        if exist:
            multiview_data = {}
            image_infos = []
            for c in range(num_cameras):
                singleview_data = input_data[c]
                image_file = singleview_data['image_file']
                # load image
                file_client = mmcv.FileClient(backend='disk')
                img_bytes = file_client.get(image_file)
                img = mmcv.imfrombytes(
                    img_bytes, flag='color', channel_order='rgb')
                # img = img.astype(np.float32)
                # get image scale
                height, width, _ = img.shape
                input_size = config_dict['model']['human_detector']['image_size']
                center = np.array((width / 2, height / 2), dtype=np.float32)
                scale = get_scale(input_size, (width, height))
                mat_input = get_affine_transform(
                    center=center,
                    scale=scale / 200.0,
                    rot=0.0,
                    output_size=input_size)
                img = cv2.warpAffine(img, mat_input,
                                     (int(input_size[0]), int(input_size[1])))
                image_infos.append(input_data[c])

                singleview_data['img'] = img
                singleview_data['center'] = center
                singleview_data['scale'] = scale
                multiview_data[c] = singleview_data

            multiview_data = pipeline(multiview_data)
            # TODO: inference with input_heatmaps/kpts_2d
            multiview_data = collate([multiview_data], samples_per_gpu=1)
            multiview_data = scatter(multiview_data, [args.device])[0]

            with torch.no_grad():
                print_json(
                    model,
                    **multiview_data,
                    input_heatmaps=None,
                    dataset_info=dataset_info,
                    out_dir=args.out_img_root
                )
        else:
            print('no real time image data detected')
            time.sleep(0.5)




if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument(
        '--out-img-root', type=str, default='', help='Output image root')

    parser.add_argument(
        '--visualize-single-view',
        action='store_true',
        default=False,
        help='whether to visualize single view imgs')
    parser.add_argument(
        '--show',
        action='store_true',
        default=False,
        help='whether to show img')
    parser.add_argument(
        '--device', default='cuda:0', help='Device for inference')
    parser.add_argument(
        '--radius',
        type=int,
        default=8,
        help='Keypoint radius for visualization')
    parser.add_argument(
        '--thickness',
        type=int,
        default=8,
        help='Link thickness for visualization')

    args = parser.parse_args()
    if not osp.exists('voxelpose_prn64x64x64_cpn80x80x20_panoptic_cam5-545c150e_20211103.pth'):
        print('no check point detected, downloading it')
        remote_url = 'https://download.openmmlab.com/mmpose/body3d/voxelpose/voxelpose_prn64x64x64_cpn80x80x20_panoptic_cam5-545c150e_20211103.pth'
        # Define the local filename to save data
        local_file = 'voxelpose_prn64x64x64_cpn80x80x20_panoptic_cam5-545c150e_20211103.pth'
        # Make http request for remote file data
        download(remote_url, local_file)

    inference(args)
