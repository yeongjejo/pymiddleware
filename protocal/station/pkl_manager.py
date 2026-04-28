import threading
import joblib
import numpy as np
from scipy.spatial.transform import Rotation as R
import json


import time

from singleton_manager import SingletonManager


class PklManager(threading.Thread):
    def __init__(self, file_path):
        super().__init__()
        self._running = True
        self.file_path = file_path

    def stop(self):
        self.join()  # 스레드가 종료될 때까지 대기

    def run(self):
        data = joblib.load(self.file_path)

        # dict_keys(['time', 'shot', 'frame_path', 'tracked_ids', 'tracked_bbox', 'tid', 'bbox', 'tracked_time', 'appe', 'loca', 'pose', 'center', 'scale', 'size', 'img_path', 'img_name', 'class_name', 'conf', 'annotations', 'smpl', 'camera', 'camera_bbox', '3d_joints', '2d_joints', 'mask', 'extra_data'])
        for i in data.values():
            body_pose = np.array(i['smpl'][0]['body_pose'], dtype=np.float64)
            global_orient = np.array(i['smpl'][0]['global_orient'], dtype=np.float64)

            r = R.from_matrix(body_pose)
            root_r = R.from_matrix(global_orient)
            #
            # protocal_angle = [0, 3, 2, 1]
            #
            # flip = R.from_euler('z', np.pi / 2)  # up 변환
            # # rot = R.from_euler('y', np.pi)  # forward 보정
            #
            # r = flip * r
            #
            # quats_wxyz = r.as_quat()[:, [3, 0, 1, 2]].tolist()
            #
            #
            # root_quats_wxyz = root_r.as_quat()[:, protocal_angle].tolist()
            #
            #
            # # 2순위
            # root_quats_wxyz[0][3] *= -1  # Z
            # #
            # # # 3순위
            # root_quats_wxyz[0][1] *= -1  # X
            #
            # # quats_wxyz[:, 2] *= -1  # Y
            # # quats_wxyz[:, 3] *= -1  # Z
            # # quats_wxyz[:, 1] *= -1  # X
            #
            # # quats_wxyz = quats_wxyz.tolist()  # 마지막에 변환
            #
            #
            test = [1.0, 0.0, 0.0, 0.0]
            # print(quats_wxyz)
            #

            frame_rotation = []
            body_pose = np.array(i['smpl'][0]['body_pose'], dtype=np.float64)
            global_orient = np.array(i['smpl'][0]['global_orient'], dtype=np.float64)

            r = R.from_matrix(body_pose)
            root_r = R.from_matrix(global_orient)

            # 루트
            convert = R.from_euler('x', -np.pi)
            root_r = convert * root_r
            root_quats_wxyz = root_r.as_quat()[:, [3, 0, 1, 2]].tolist()
            frame_rotation.append(root_quats_wxyz[0])

            # 가슴
            # quats_wxyz = r.as_quat()[8, [3, 2, 1, 0]].tolist()
            # frame_rotation.append(quats_wxyz)
            frame_rotation.append(test)



            # 오른 어퍼암
            quats_wxyz = r.as_quat()[16, [3, 2, 0, 1]].tolist()
            quats_wxyz[3] *= -1.0
            quats_wxyz[1] *= -1.0
            frame_rotation.append(quats_wxyz)

            # 오른 로우암
            quats_wxyz = r.as_quat()[18, [3, 2, 0, 1]].tolist()
            quats_wxyz[3] *= -1.0
            quats_wxyz[2] *= -1.0
            frame_rotation.append(quats_wxyz)

            #왼 어퍼암
            quats_wxyz = r.as_quat()[15, [3, 2, 1, 0]].tolist()
            quats_wxyz[1] *= -1.0
            frame_rotation.append(quats_wxyz)

            #왼 로우암
            quats_wxyz = r.as_quat()[17, [3, 2, 1, 0]].tolist()
            quats_wxyz[1] *= -1.0
            frame_rotation.append(quats_wxyz)

            # #왼 업레그
            quats_wxyz = r.as_quat()[0, [3, 0, 2, 1]].tolist()
            quats_wxyz[1] *= -1.0
            frame_rotation.append(quats_wxyz)

            # 왼 로우 레그
            quats_wxyz = r.as_quat()[3, [3, 0, 2, 1]].tolist()
            quats_wxyz[1] *= -1.0
            frame_rotation.append(quats_wxyz)

            # # 오른 업 레그
            quats_wxyz = r.as_quat()[1, [3, 2, 0, 1]].tolist()
            frame_rotation.append(quats_wxyz)

            # 오른 로우 레그
            quats_wxyz = r.as_quat()[4, [3, 2, 0, 1]].tolist()
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
            # frame_rotation = [root_quats_wxyz[0], test, test, test,
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
            time.sleep(0.056)  # 약 60FPS
            # print('실시간 전송')
            # print(root_quats_wxyz[0])


