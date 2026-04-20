from tokenize import Single

from sensor.sensor_part import SensorPart


class DataManager():
    __sensor_data = {part: [] for part in SensorPart}

    __acc_pickle_data = []
    __ori_pickle_data = []

    @property
    def sensor_data(self):
        return self.__sensor_data

    @sensor_data.setter
    def sensor_data(self, data):
        self.__sensor_data[data[0]] = data[1]

    def set_sensor_value(self, key, value):
        self.__sensor_data[key] = value


    def set_pickle_data(self, bridge, finger_value):
        part_sequence = [SensorPart.WAIST, SensorPart.BACK, SensorPart.RIGHT_UPPER_ARM, SensorPart.RIGHT_LOWER_ARM,
                            SensorPart.LEFT_UPPER_ARM, SensorPart.LEFT_LOWER_ARM, SensorPart.LEFT_UPPER_LEG, SensorPart.LEFT_LOWER_LEG
                            , SensorPart.RIGHT_UPPER_LEG,SensorPart.RIGHT_LOWER_LEG
                         ]

        frame_acc_sensor_data = []
        frame_ori_sensor_data = []
        frame_hand_sensor_data = []
        frame_smpl_sensor_data = []
        for part in part_sequence:
            try:
                frame_smpl_sensor_data.append(self.__sensor_data[part][3])
                frame_hand_sensor_data.append(self.__sensor_data[part][3])
                if part == SensorPart.LEFT_HAND or part == SensorPart.RIGHT_HAND:
                    continue

                frame_acc_sensor_data.append(
                    [self.__sensor_data[part][1].x, self.__sensor_data[part][1].y, self.__sensor_data[part][1].z])
                frame_ori_sensor_data.append([self.__sensor_data[part][3].w, self.__sensor_data[part][3].x, self.__sensor_data[part][3].y, self.__sensor_data[part][3].z])
            except Exception as e:
                print(part)
                print("에러 내용:", e)
                # print(self.__sensor_data)
                print(self.__sensor_data[part][1])
                print(self.__sensor_data[part][3])
                return

        if bridge is not None:
            bridge.send_test_frame(frame_ori_sensor_data, finger_value)



        self.__acc_pickle_data.append(frame_acc_sensor_data)
        self.__ori_pickle_data.append(frame_ori_sensor_data)

