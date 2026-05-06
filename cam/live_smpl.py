import threading
from pathlib import Path
import torch
import argparse
import os
import cv2
import numpy as np
from scipy.spatial.transform import Rotation as R
import json
import time

from cam.hmr2.configs import CACHE_DIR_4DHUMANS
from cam.hmr2.models import HMR2, download_models, load_hmr2, DEFAULT_CHECKPOINT
from cam.hmr2.utils import recursive_to
from cam.hmr2.datasets.vitdet_dataset import ViTDetDataset, DEFAULT_MEAN, DEFAULT_STD
from cam.hmr2.utils.renderer import Renderer, cam_crop_to_full
from singleton_manager import SingletonManager

LIGHT_BLUE = (0.65098039, 0.74117647, 0.85882353)

class LiveSmpl(threading.Thread):
    def __init__(self):
        super().__init__()
        self.camera_send_start = False

    def stop(self):
        self.join()  # 스레드가 종료될 때까지 대기

    def run(self):
        rendering = True
        detector_list = ['vitdet', 'regnety']
        selected_detector = detector_list[0]

        # Download and load checkpoints
        download_models(CACHE_DIR_4DHUMANS)
        model, model_cfg = load_hmr2(DEFAULT_CHECKPOINT)

        # Setup HMR2.0 model
        device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
        model = model.to(device)
        model.eval()

        # Load detector
        from cam.hmr2.utils.utils_detectron2 import DefaultPredictor_Lazy
        if selected_detector == 'vitdet':
            from detectron2.config import LazyConfig
            import cam.hmr2 as hmr2
            cfg_path = Path(hmr2.__file__).parent / 'configs' / 'cascade_mask_rcnn_vitdet_h_75ep.py'
            detectron2_cfg = LazyConfig.load(str(cfg_path))
            detectron2_cfg.train.init_checkpoint = "https://dl.fbaipublicfiles.com/detectron2/ViTDet/COCO/cascade_mask_rcnn_vitdet_h/f328730692/model_final_f05665.pkl"
            for i in range(3):
                detectron2_cfg.model.roi_heads.box_predictors[i].test_score_thresh = 0.25
            detector = DefaultPredictor_Lazy(detectron2_cfg)
        elif selected_detector == 'regnety':
            from detectron2 import model_zoo
            from detectron2.config import get_cfg
            detectron2_cfg = model_zoo.get_config('new_baselines/mask_rcnn_regnety_4gf_dds_FPN_400ep_LSJ.py',
                                                  trained=True)
            detectron2_cfg.model.roi_heads.box_predictor.test_score_thresh = 0.5
            detectron2_cfg.model.roi_heads.box_predictor.test_nms_thresh = 0.4
            detector = DefaultPredictor_Lazy(detectron2_cfg)

        # Setup the renderer
        renderer = Renderer(model_cfg, faces=model.smpl.faces)

        # Iterate over all images in folder
        # for img_path in img_paths:
        cap = cv2.VideoCapture(0)  # 0 = 기본 웹캠


        while True:
            if SingletonManager().bridge is not None:
                SingletonManager().bridge.send_start_camera(self)

            start = time.time()

            ret, frame = cap.read()
            if not ret:
                break

            img_cv2 = frame
            # Detect humans in image
            det_out = detector(img_cv2)

            det_instances = det_out['instances']
            valid_idx = (det_instances.pred_classes == 0) & (det_instances.scores > 0.5)
            boxes = det_instances.pred_boxes.tensor[valid_idx].cpu().numpy()

            # Run HMR2.0 on all detected humans
            dataset = ViTDetDataset(model_cfg, img_cv2, boxes)
            dataloader = torch.utils.data.DataLoader(dataset, batch_size=8, shuffle=False, num_workers=0)

            all_verts = []
            all_cam_t = []

            for batch in dataloader:
                batch = recursive_to(batch, device)
                with torch.no_grad():
                    out = model(batch)

                if self.camera_send_start:
                    self.send_camera_data(out)

                pred_cam = out['pred_cam']
                box_center = batch["box_center"].float()
                box_size = batch["box_size"].float()
                img_size = batch["img_size"].float()
                scaled_focal_length = model_cfg.EXTRA.FOCAL_LENGTH / model_cfg.MODEL.IMAGE_SIZE * img_size.max()
                pred_cam_t_full = cam_crop_to_full(pred_cam, box_center, box_size, img_size,
                                                   scaled_focal_length).detach().cpu().numpy()


                # Render the result
                batch_size = batch['img'].shape[0]
                for n in range(batch_size):
                    # Add all verts and cams to list
                    verts = out['pred_vertices'][n].detach().cpu().numpy()
                    cam_t = pred_cam_t_full[n]
                    all_verts.append(verts)
                    all_cam_t.append(cam_t)

            # Render front view
            if rendering and len(all_verts) > 0:
                misc_args = dict(
                    mesh_base_color=LIGHT_BLUE,
                    scene_bg_color=(1, 1, 1),
                    focal_length=scaled_focal_length,
                )
                cam_view = renderer.render_rgba_multiple(all_verts, cam_t=all_cam_t, render_res=img_size[n],
                                                         **misc_args)

                # Overlay image
                input_img = img_cv2.astype(np.float32)[:, :, ::-1] / 255.0
                input_img = np.concatenate([input_img, np.ones_like(input_img[:, :, :1])], axis=2)  # Add alpha channel
                input_img_overlay = input_img[:, :, :3] * (1 - cam_view[:, :, 3:]) + cam_view[:, :, :3] * cam_view[
                    :, :, 3:]


                img = (255 * input_img_overlay[:, :, ::-1]).astype(np.uint8)
                # h, w = img.shape[:2]
                #
                # scale = 0.5  # 50% 축소
                # img_resized = cv2.resize(img, (int(w * scale), int(h * scale)))
                # cv2.imshow("Webcam", img_resized)
                cv2.imshow("Webcam", img)
            else:
                cv2.imshow("Webcam", img_cv2)

            if cv2.waitKey(1) & 0xFF == 27:  # ESC 누르면 종료
                break

            end = time.time()
            print(end - start)


    def send_camera_data(self, data):
        frame_rotation = []
        body_pose = data['pred_smpl_params']['body_pose'].detach().cpu().numpy().astype(np.float64)
        global_orient = data['pred_smpl_params']['global_orient'].detach().cpu().numpy().astype(np.float64)

        # batch 차원 제거
        body_pose = body_pose[0]  # (1, 23, 3, 3) -> (23, 3, 3)
        global_orient = global_orient[0]  # (1, 1, 3, 3) 또는 (1, 3, 3) -> (1, 3, 3) / (3, 3)

        if global_orient.ndim == 3 and global_orient.shape[0] == 1:
            global_orient = global_orient[0]  # (1, 3, 3) -> (3, 3)


        # TODO:
        #  - 축 맞추기 진행 해야됨 (현재 three js 축이랑 안맞음)
        #  - 아래 방식 말고 다른 방식으로 축 맞춰도됨
        C = np.array([
            [-1, 0, 0],
            [0, 0, -1],
            [0, -1, 0]
        ], dtype=np.float64)

        body_pose_new = C @ body_pose @ C.T
        global_orient_new = C @ global_orient @ C.T

        r = R.from_matrix(body_pose_new)
        root_r = R.from_matrix(global_orient_new)

        # 루트
        convert = R.from_euler('x', -np.pi)


        root_r = convert * root_r
        root_quats_wxyz = root_r.as_quat()[[3, 0, 1, 2]].tolist()
        frame_rotation.append(root_quats_wxyz)

        # 가슴
        quats_wxyz = r.as_quat()[8, [3, 0, 1, 2]].tolist()
        frame_rotation.append(quats_wxyz)
        # frame_rotation.append(test)

        # 오른 어퍼암
        quats_wxyz = r.as_quat()[16, [3, 0, 1, 2]].tolist()
        frame_rotation.append(quats_wxyz)

        # 오른 로우암
        quats_wxyz = r.as_quat()[18, [3, 0, 1, 2]].tolist()
        frame_rotation.append(quats_wxyz)

        # 왼 어퍼암
        quats_wxyz = r.as_quat()[15, [3, 0, 1, 2]].tolist()
        frame_rotation.append(quats_wxyz)

        # 왼 로우암
        quats_wxyz = r.as_quat()[17, [3, 0, 1, 2]].tolist()
        frame_rotation.append(quats_wxyz)

        # #왼 업레그
        quats_wxyz = r.as_quat()[0, [3, 0, 1, 2]].tolist()
        frame_rotation.append(quats_wxyz)

        # 왼 로우 레그
        quats_wxyz = r.as_quat()[3, [3, 0, 1, 2]].tolist()
        frame_rotation.append(quats_wxyz)

        # # 오른 업 레그
        quats_wxyz = r.as_quat()[1, [3, 0, 1, 2]].tolist()
        frame_rotation.append(quats_wxyz)

        # 오른 로우 레그
        quats_wxyz = r.as_quat()[4, [3, 0, 1, 2]].tolist()
        frame_rotation.append(quats_wxyz)

        # print(frame_rotation)

        # 4458

        # frame_rotation = [root_quats_wxyz[0], quats_wxyz[8], quats_wxyz[16], quats_wxyz[18],
        #                   quats_wxyz[15], quats_wxyz[17], quats_wxyz[0], quats_wxyz[3],
        #                   quats_wxyz[1], quats_wxyz[4]]
        #
        # frame_rotation = [test, quats_wxyz[8], quats_wxyz[16], quats_wxyz[18],
        #                   quats_wxyz[15], quats_wxyz[17], quats_wxyz[0], quats_wxyz[3],
        #                   quats_wxyz[1], quats_wxyz[4]]

        # frame_rotation = [test, test, test, test,
        #                   test, test, test, test,
        #                    quats_wxyz ,test]

        #
        # frame_rotation = [root_quats_wxyz[0], test, quats_wxyz, test,
        #                   test, test, test, test,
        #                   test,test]
        #
        # frame_rotation = [test, test, test, test,
        #                   test, test, test, test,
        #                   test,test]

        payload = {
            "frameBoneRotation": frame_rotation,
        }

        # Python -> JS 실시간 전송
        # print("bridge test : ", SingletonManager().bridge)
        SingletonManager().bridge.pklUpdated.emit(json.dumps(payload))