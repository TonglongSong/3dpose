import sys
import os.path as osp
import numpy as np
import cv2
import math
import torch
import torchvision.transforms as transforms
from torch.nn.parallel.data_parallel import DataParallel
import torch.backends.cudnn as cudnn
from rootnet.main.config import cfg
from rootnet.main.model import get_pose_net
from rootnet.common.utils.pose_utils import process_bbox
from rootnet.data.dataset import generate_patch_image
import timeit


def load_rootnet_data():
    cfg.set_args('0')
    cudnn.benchmark = True

    # snapshot load
    model_path = './snapshot_%d.pth.tar' % int(18)
    assert osp.exists(model_path), 'Cannot find model at ' + model_path
    print('Load checkpoint from {}'.format(model_path))
    model = get_pose_net(cfg, False)
    model = DataParallel(model).cuda()
    ckpt = torch.load(model_path)
    model.load_state_dict(ckpt['network'])
    model.eval()
    print(f"rootnet model loaded")
    return model


def findrootdepth(bbox, focal, original_img, model):
        # prepare input image
    transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize(mean=cfg.pixel_mean, std=cfg.pixel_std)])
    original_img_height, original_img_width = original_img.shape[:2]

    # prepare bbox for each human
    bbox_list = bbox  # xmin, ymin, width, height
    person_num = len(bbox_list)

    # normalized camera intrinsics
    princpt = [original_img_width / 2, original_img_height / 2]  # x-axis, y-axis

    # for cropped and resized human image, forward it to RootNet
    output = []
    for n in range(person_num):
        bbox = process_bbox(np.array(bbox_list[n]), original_img_width, original_img_height)
        img, img2bb_trans = generate_patch_image(original_img, bbox, False, 0.0)
        img = transform(img).cuda()[None, :, :, :]
        k_value = np.array(
            [math.sqrt(cfg.bbox_real[0] * cfg.bbox_real[1] * focal[0] * focal[1] / (bbox[2] * bbox[3]))]).astype(
            np.float32)
        k_value = torch.FloatTensor([k_value]).cuda()[None, :]

        # forward
        with torch.no_grad():
            root_3d = model(img, k_value)  # x,y: pixel, z: root-relative depth (mm)
        root_3d = root_3d[0].cpu().numpy()

        output.append(root_3d[2])
    return output


