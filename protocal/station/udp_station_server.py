import threading
import socket
import struct

from data_manager import DataManager
from sensor.acc import Acc
from sensor.gyro import Gyro
from sensor.mag import Mag
from sensor.quaternion import Quaternion
from sensor.sensor_part import SensorPart

import numpy as np
from scipy.spatial.transform import Rotation as R


import torch
import math

from sensor.station_info import StationInfo


class UDPServer(threading.Thread):
    testX = 0
    testY = 0
    testZ = 0

    def __init__(self, port, bridge):
        super().__init__()
        self._running = True
        self.port = port
        self.bridge = bridge
        self.datamanager = DataManager()
        self.check = False # 프론트로 데이터 전송 여뷰
        self.tpose = False

        self.basic_sensor_part = [SensorPart.LEFT_LOWER_ARM, SensorPart.RIGHT_LOWER_ARM, SensorPart.LEFT_LOWER_LEG,
                                 SensorPart.RIGHT_LOWER_LEG, SensorPart.BACK, SensorPart.WAIST, SensorPart.LEFT_UPPER_LEG,
                                      SensorPart.RIGHT_UPPER_LEG, SensorPart.LEFT_UPPER_ARM, SensorPart.RIGHT_UPPER_ARM
                                    ]

        self.axis_swap_quat_map = {
            sensor_part: Quaternion(1.0, 0.0, 0.0, 0.0)
            for sensor_part in self.basic_sensor_part
        }
        self.init_quat_map = {
            sensor_part: Quaternion(1.0, 0.0, 0.0, 0.0)
            for sensor_part in self.basic_sensor_part
        }

    def stop(self):
        self._running = False  # 스레드 종료 플래그 설정
        self.join()  # 스레드가 종료될 때까지 대기

    def run(self):
        self._running = True

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', self.port))
        station_info = StationInfo()

        fing_max = [1] * 10
        fing_mim = [99999] * 10

        while self._running:
            # buffer = bytearray(907)  # 수신할 데이터 사이즈 설정
            buffer = bytearray(949)  # 수신할 데이터 사이즈 설정

            # print("000000000000000000")
            # 데이터 수신
            sock.recv_into(buffer)

            # print("데이터 수신 확인")

            # 데이터 확인
            receive_station_byte_data = buffer

            # print(receive_station_byte_data)
            # continue

            # 헤더 데이터 저장
            station_info.header = [receive_station_byte_data[0], receive_station_byte_data[1]]

            # 버전 저장
            station_info.version = receive_station_byte_data[2] & 0xFF

            # 센서 데이터 저장
            # iMotion_Parsing_(PIP packet)241016_파이썬_파싱 문서 참고
            start_byte_num = 3

            while True:
                # 모든센서 저장이 끝나면 종료
                # if start_byte_num > 852:
                if start_byte_num > 926:
                    break

                sensor_byte_data = receive_station_byte_data[start_byte_num:start_byte_num + 53]  # 추출할 센서 데이터
                start_byte_num += 53  # 다음 탐색할 센서의 바이트 시작 번호

                # 센서 번호 저장
                try:
                    sensor_part = SensorPart(sensor_byte_data[0] & 0xFF)
                    # print(sensor_part)
                except ValueError:
                    continue

                # 자이로 x, y, z 계산
                gyroX = self.cul_byte_data(sensor_byte_data[1:5])
                gyroY = self.cul_byte_data(sensor_byte_data[5:9])
                gyroZ = self.cul_byte_data(sensor_byte_data[9:13])
                gyro = Gyro(gyroX, gyroY, gyroZ)

                # 가속도 x, y, z 계산
                accX = self.cul_byte_data(sensor_byte_data[13:17])
                accY = self.cul_byte_data(sensor_byte_data[17:21])
                accZ = self.cul_byte_data(sensor_byte_data[21:25])
                raw_acc = Acc(accX, accY, accZ)
                acc = Acc(accX, accY, accZ)
                # acc = Acc(accY, accZ, accX)
                # acc.norm()

                # 자기계 x, y, z 계산
                magX = self.cul_byte_data(sensor_byte_data[25:29])
                magY = self.cul_byte_data(sensor_byte_data[29:33])
                magZ = self.cul_byte_data(sensor_byte_data[33:37])
                mag = Mag(magX, magY, magZ)

                # 쿼터니언 w, x, y, z 계산
                qW = self.cul_byte_data(sensor_byte_data[37:41])
                qX = self.cul_byte_data(sensor_byte_data[41:45])
                qY = self.cul_byte_data(sensor_byte_data[45:49])
                qZ = self.cul_byte_data(sensor_byte_data[49:53])

                if qW == 0.0:
                    continue

                # 파이썬에서는 이렇게 하니깐 각도가 깨짐
                # hip_leg_part_list = [SensorPart.LEFT_LOWER_LEG, SensorPart.RIGHT_LOWER_LEG,
                #                     SensorPart.WAIST, SensorPart.LEFT_UPPER_LEG, SensorPart.RIGHT_UPPER_LEG]
                # if sensor_part in hip_leg_part_list:
                #     self.axis_swap_quat_map[sensor_part] = Quaternion(qW, qY, -qX, qZ)
                # else:
                #     self.axis_swap_quat_map[sensor_part] = Quaternion(qW, qX, qY, qZ)

                self.axis_swap_quat_map[sensor_part] = Quaternion(qW, qX, qY, qZ)

                # todo Tpose 테스트용
                if sensor_part in self.basic_sensor_part and self.tpose:
                    self.set_init_quaternion(sensor_part)

                tpose_quat_wxyz = self.convert_to_tpose_quat(sensor_part)

                #
                if sensor_part in [SensorPart.WAIST, SensorPart.BACK]:
                    final_quat = Quaternion(tpose_quat_wxyz.w, tpose_quat_wxyz.x, -tpose_quat_wxyz.z, tpose_quat_wxyz.y)
                elif sensor_part in [SensorPart.RIGHT_LOWER_LEG, SensorPart.RIGHT_UPPER_LEG, SensorPart.RIGHT_UPPER_ARM, SensorPart.RIGHT_LOWER_ARM]:
                    final_quat = Quaternion(tpose_quat_wxyz.w, tpose_quat_wxyz.y, -tpose_quat_wxyz.z, -tpose_quat_wxyz.x)
                elif sensor_part in [SensorPart.LEFT_LOWER_LEG, SensorPart.LEFT_UPPER_LEG, SensorPart.LEFT_UPPER_ARM, SensorPart.LEFT_LOWER_ARM]:
                    final_quat = Quaternion(tpose_quat_wxyz.w, -tpose_quat_wxyz.y, -tpose_quat_wxyz.z, tpose_quat_wxyz.x)
                else:
                    final_quat = Quaternion(tpose_quat_wxyz.w, tpose_quat_wxyz.x, tpose_quat_wxyz.y, tpose_quat_wxyz.z)

                final_quat.norm()


                # if sensor_part in [SensorPart.RIGHT_UPPER_LEG, SensorPart.RIGHT_LOWER_LEG]:
                    # print(sensor_part, " : ", self.init_quat_map[sensor_part], self.axis_swap_quat_map[sensor_part], final_quat)

                # print(f"part222 = {sensor_part} w = {quaternion.w}, x = {quaternion.x}, y = {quaternion.y}, z = {quaternion.z}")
                # if (sensor_part in sensor_part_list and accX == 0.0 and accY == 0.0):
                    # print(f"part222 = {sensor_part}")
                    # print(f"part222 = {sensor_part} x = {acc.x}, y = {acc.y}, z = {acc.z}")
                    # print(
                    #     f"part222 = {sensor_part} w = {quaternion.w}, x = {quaternion.x}, y = {quaternion.y}, z = {quaternion.z}")
                    # cheeck = True
                    # continue


                # 센서 정보 저장
                self.datamanager.sensor_data = [sensor_part, [gyro, acc, mag, final_quat]]


            l_finger_e = self.cul_byte_finger_data(receive_station_byte_data[905:907])
            l_finger_d = self.cul_byte_finger_data(receive_station_byte_data[909:911])
            l_finger_c = self.cul_byte_finger_data(receive_station_byte_data[913:915])
            l_finger_b = self.cul_byte_finger_data(receive_station_byte_data[917:919])
            l_finger_a = self.cul_byte_finger_data(receive_station_byte_data[921:923])

            r_finger_a = self.cul_byte_finger_data(receive_station_byte_data[926:928])
            r_finger_b = self.cul_byte_finger_data(receive_station_byte_data[930:932])
            r_finger_c = self.cul_byte_finger_data(receive_station_byte_data[934:936])
            r_finger_d = self.cul_byte_finger_data(receive_station_byte_data[938:940])
            r_finger_e = self.cul_byte_finger_data(receive_station_byte_data[942:944])


            # print("손가락 확인", l_finger_a, l_finger_b, l_finger_c, l_finger_d, l_finger_e)
            # print("손가락 확인", r_finger_a, r_finger_b, r_finger_c, r_finger_d, r_finger_e)
            # print("손가락 확인", l_finger_a)
            # print("-----------------------------")

            finger_list = [r_finger_a, r_finger_b, r_finger_c, r_finger_d, r_finger_e, l_finger_c, l_finger_d, l_finger_a, l_finger_b, l_finger_e]

            # print(fing_mim)
            # print(finger_list)

            finger_value = []
            for i, value in enumerate(finger_list):
                # min max 설정
                if fing_max[i] < value:
                    fing_max[i] = value
                if fing_mim[i] > value:
                    fing_mim[i] = value

                normalized = [2 + max((value - fing_mim[i]), 1) * (100 - 2) / max((fing_max[i] - fing_mim[i]), 1)] * 4
                finger_value = finger_value + normalized


            # print(finger_value)
            #
            # print("-----------------------------")

            self.tpose = False
            # print(DataManager().sensor_data)
            # todo 추후 삭제 또는 이동
            if self.check:
                self.datamanager.set_sensor_data(self.bridge, finger_value)

        sock.close()

    def set_init_quaternion(self, sensor_part):
        self.init_quat_map[sensor_part] = Quaternion(self.axis_swap_quat_map[sensor_part].w, self.axis_swap_quat_map[sensor_part].x, self.axis_swap_quat_map[sensor_part].y, self.axis_swap_quat_map[sensor_part].z)

    def cul_byte_data(self, sensor_data):
        int_bits = (sensor_data[3] & 0xFF) << 24 | \
                   (sensor_data[2] & 0xFF) << 16 | \
                   (sensor_data[1] & 0xFF) << 8 | \
                   (sensor_data[0] & 0xFF)

        float_value = struct.unpack('<f', struct.pack('<I', int_bits))[0]
        return float_value

    def cul_byte_finger_data(self, sensor_data):
        int_bits = (sensor_data[0]) << 8 | (sensor_data[1])
        # int_bits = (sensor_data[1] & 0xFF) << 8  | \
        #             (sensor_data[0] & 0xFF)

        float_value = np.float16(int_bits)
        return int_bits

    def rotation_matrix_to_euler_angle(self, r: torch.Tensor, seq='XYZ'):
        """
        Turn rotation matrices into euler angles. (torch, batch)

        :param r: Rotation matrix tensor that can reshape to [batch_size, 3, 3].
        :param seq: 3 characters belonging to the set {'X', 'Y', 'Z'} for intrinsic
                    rotations, or {'x', 'y', 'z'} for extrinsic rotations (radians).
                    See scipy for details.
        :return: Euler angle tensor of shape [batch_size, 3].
        """
        from scipy.spatial.transform import Rotation
        rot = Rotation.from_matrix(r.clone().detach().cpu().view(-1, 3, 3).numpy())
        ret = torch.from_numpy(rot.as_euler(seq)).float().to(r.device)

        # print(ret)
        return torch.round(ret * 10000) / 10000

    def quat_to_wxyz_array(self, q):
        """
        Quaternion 객체 또는 [w, x, y, z] 배열을 numpy 배열로 변환
        """

        # 사용자 정의 Quaternion 클래스인 경우
        if hasattr(q, "w") and hasattr(q, "x") and hasattr(q, "y") and hasattr(q, "z"):
            return np.array([q.w, q.x, q.y, q.z], dtype=np.float64)

        # 이미 list, tuple, np.ndarray인 경우
        q = np.asarray(q, dtype=np.float64)

        if q.shape != (4,):
            raise ValueError(f"Quaternion must have 4 values [w, x, y, z], but got shape {q.shape}")

        return q

    def eigen_to_scipy_quat(self, q_wxyz):
        """
        Eigen Quaterniond 순서 [w, x, y, z]
        -> scipy 순서 [x, y, z, w]
        """

        q_wxyz = self.quat_to_wxyz_array(q_wxyz)

        return np.array([
            q_wxyz[1],
            q_wxyz[2],
            q_wxyz[3],
            q_wxyz[0]
        ], dtype=np.float64)

    def scipy_to_eigen_quat(self, q_xyzw):
        """
        scipy 순서 [x, y, z, w] -> Eigen Quaterniond 순서 [w, x, y, z]
        """
        q_xyzw = np.asarray(q_xyzw, dtype=np.float64)
        return np.array([q_xyzw[3], q_xyzw[0], q_xyzw[1], q_xyzw[2]], dtype=np.float64)

    def suit_quat2angle(self, q_wxyz):
        """
        Quaternion -> Euler angle [x, y, z]
        """

        # 기존 코드의 self.eigen_to_scipy_quat(self, q_wxyz)는 잘못됨
        q_xyzw = self.eigen_to_scipy_quat(q_wxyz)

        rot = R.from_quat(q_xyzw)

        euler = rot.as_euler("xyz", degrees=False)

        return euler

    def normalize_quat_xyzw(self, q):
        q = np.asarray(q, dtype=np.float64)
        norm = np.linalg.norm(q)
        if norm == 0:
            raise ValueError("Quaternion norm is zero")
        return q / norm

    def convert_to_tpose_quat(self, sensor_part):
        # print(self.axis_swap_quat)

        # Quaternion 객체에서 [w, x, y, z] 배열로 변환
        present_quat_wxyz = self.quat_to_wxyz_array(self.axis_swap_quat_map[sensor_part])
        init_quat_wxyz = self.quat_to_wxyz_array(self.init_quat_map[sensor_part])

        # scipy용 쿼터니언 변환 [x, y, z, w]
        present_quat_xyzw = self.normalize_quat_xyzw(
            self.eigen_to_scipy_quat(present_quat_wxyz)
        )

        init_quat_xyzw = self.normalize_quat_xyzw(
            self.eigen_to_scipy_quat(init_quat_wxyz)
        )

        present_rot = R.from_quat(present_quat_xyzw)
        init_rot = R.from_quat(init_quat_xyzw)

        # init quaternion의 yaw 추출
        q2a = self.suit_quat2angle(init_quat_wxyz)
        yaw = q2a[2]

        # yaw 회전 쿼터니언
        twist_rot = R.from_quat([
            0.0,
            0.0,
            np.sin(yaw / 2.0),
            np.cos(yaw / 2.0)
        ])

        x_axis = twist_rot.apply(np.array([1.0, 0.0, 0.0]))
        y_axis = twist_rot.apply(np.array([0.0, 1.0, 0.0]))
        z_axis = twist_rot.apply(np.array([0.0, 0.0, 1.0]))

        # deltaQ = presentQuat * init.conjugate()
        delta_rot = present_rot * init_rot.inv()

        x_rot = delta_rot.apply(x_axis)
        y_rot = delta_rot.apply(y_axis)
        z_rot = delta_rot.apply(z_axis)

        # -yaw 보정
        minus_yaw = -yaw

        yaw_correction_rot = R.from_quat([
            0.0,
            0.0,
            np.sin(minus_yaw / 2.0),
            np.cos(minus_yaw / 2.0)
        ])

        x_rot = yaw_correction_rot.apply(x_rot)
        y_rot = yaw_correction_rot.apply(y_rot)
        z_rot = yaw_correction_rot.apply(z_rot)

        x_rot = x_rot / np.linalg.norm(x_rot)
        y_rot = y_rot / np.linalg.norm(y_rot)
        z_rot = z_rot / np.linalg.norm(z_rot)

        mat = np.column_stack([x_rot, y_rot, z_rot])

        tpose_rot = R.from_matrix(mat)

        # scipy 결과 [x, y, z, w]
        tpose_quat_xyzw = self.normalize_quat_xyzw(tpose_rot.as_quat())

        # Eigen 순서 [w, x, y, z]
        tpose_quat_wxyz = self.scipy_to_eigen_quat(tpose_quat_xyzw)

        return Quaternion(tpose_quat_wxyz[0], tpose_quat_wxyz[1], tpose_quat_wxyz[2], tpose_quat_wxyz[3])

    def get_coordinate_dict(self, w, x, y, z, acc_x, acc_y, acc_z):
        acc_init = 1.2
        coordinate_dict = {
            # 모두 양수일 경우
            0: [Quaternion(w, x, y, z), Acc(acc_x, acc_y, acc_z)],
            1: [Quaternion(w, x, z, y), Acc(acc_x, acc_z, acc_y)],
            2: [Quaternion(w, y, x, z), Acc(acc_y, acc_x, acc_z)],
            3: [Quaternion(w, y, z, x), Acc(acc_y, acc_z, acc_x)],
            4: [Quaternion(w, z, x, y), Acc(acc_z, acc_x, acc_y)],
            5: [Quaternion(w, z, y, x), Acc(acc_z, acc_y, acc_x)],

            # x에 -1를 곱할 경우
            6: [Quaternion(w, -x, y, z), Acc(-acc_x, acc_y, acc_z)],
            7: [Quaternion(w, -x, z, y), Acc(-acc_x, acc_z, acc_y)],
            8: [Quaternion(w, y, -x, z), Acc(acc_y, -acc_x, acc_z)],
            9: [Quaternion(w, y, z, -x), Acc(acc_y, acc_z, -acc_x)],
            10: [Quaternion(w, z, -x, y), Acc(acc_z, -acc_x, acc_y)],
            11: [Quaternion(w, z, y, -x), Acc(acc_z, acc_y, -acc_x)],

            # y에 -1를 곱할 경우
            12: [Quaternion(w, x, -y, z), Acc(acc_x, -acc_y, acc_z)],
            13: [Quaternion(w, x, z, -y), Acc(acc_x, acc_z, -acc_y)],
            14: [Quaternion(w, -y, x, z), Acc(-acc_y, acc_x, acc_z)],
            15: [Quaternion(w, -y, z, x), Acc(-acc_y, acc_z, acc_x)],
            16: [Quaternion(w, z, x, -y), Acc(acc_z, acc_x, -acc_y)],
            17: [Quaternion(w, z, -y, x), Acc(acc_z, -acc_y, acc_x)],

            # z에 -1를 곱할 경우
            18: [Quaternion(w, x, y, -z), Acc(acc_x, acc_y, -acc_z)],
            19: [Quaternion(w, x, -z, y), Acc(acc_x, -acc_z, acc_y)],
            20: [Quaternion(w, y, x, -z), Acc(acc_y, acc_x, -acc_z)],
            21: [Quaternion(w, y, -z, x), Acc(acc_y, -acc_z, acc_x)],
            22: [Quaternion(w, -z, x, y), Acc(-acc_z, acc_x, acc_y)],
            23: [Quaternion(w, -z, y, x), Acc(-acc_z, acc_y, acc_x)],

            # x, y에 -1를 곱할 경우
            24: [Quaternion(w, -x, -y, z), Acc(-acc_x, -acc_y, acc_z)],
            25: [Quaternion(w, -x, z, -y), Acc(-acc_x, acc_z, -acc_y)],
            26: [Quaternion(w, -y, -x, z), Acc(-acc_y, -acc_x, acc_z)],
            27: [Quaternion(w, -y, z, -x), Acc(-acc_y, acc_z, -acc_x)],
            28: [Quaternion(w, z, -x, -y), Acc(acc_z, -acc_x, -acc_y)],
            29: [Quaternion(w, z, -y, -x), Acc(acc_z, -acc_y, -acc_x)],

            # x, z에 -1를 곱할 경우
            30: [Quaternion(w, -x, y, -z), Acc(-acc_x, acc_y, -acc_z)],
            31: [Quaternion(w, -x, -z, y), Acc(-acc_x, -acc_z, acc_y)],
            32: [Quaternion(w, y, -x, -z), Acc(acc_y, -acc_x, -acc_z)],
            33: [Quaternion(w, y, -z, -x), Acc(acc_y, -acc_z, -acc_x)],
            34: [Quaternion(w, -z, -x, y), Acc(-acc_z, -acc_x, acc_y)],
            35: [Quaternion(w, -z, y, -x), Acc(-acc_z, acc_y, -acc_x)],

            # y, z에 -1를 곱할 경우
            36: [Quaternion(w, x, -y, -z), Acc(acc_x, -acc_y, -acc_z)],
            37: [Quaternion(w, x, -z, -y), Acc(acc_x, -acc_z, -acc_y)],
            38: [Quaternion(w, -y, x, -z), Acc(-acc_y, acc_x, -acc_z)],
            39: [Quaternion(w, -y, -z, x), Acc(-acc_y, -acc_z, acc_x)],
            40: [Quaternion(w, -z, x, -y), Acc(-acc_z, acc_x, -acc_y)],
            41: [Quaternion(w, -z, -y, x), Acc(-acc_z, -acc_y, acc_x)],

            # 전부 -1를 곱할 경우
            42: [Quaternion(w, -x, -y, -z), Acc(-acc_x, -acc_y, -acc_z)],
            43: [Quaternion(w, -x, -z, -y), Acc(-acc_x, -acc_z, -acc_y)],
            44: [Quaternion(w, -y, -x, -z), Acc(-acc_y, -acc_x, -acc_z)],
            45: [Quaternion(w, -y, -z, -x), Acc(-acc_y, -acc_z, -acc_x)],
            46: [Quaternion(w, -z, -x, -y), Acc(-acc_z, -acc_x, -acc_y)],
            47: [Quaternion(w, -z, -y, -x), Acc(-acc_z, -acc_y, -acc_x)],

        }
        return coordinate_dict

