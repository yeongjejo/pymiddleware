import threading
import json

from PySide6.QtCore import Signal, Slot, QObject, QTimer, QTimerEvent
from PySide6.QtWidgets import QFileDialog, QApplication

from protocal.station.pkl_manager import PklManager
from singleton_manager import SingletonManager

class SignalBridge(QObject):
    frameUpdated = Signal(str)
    fileSelected = Signal(bool)
    stationListUpdated = Signal(str)
    setLoading= Signal(bool)
    pklUpdated = Signal(str)

    file_path = ''

    def __init__(self):
        super().__init__()
        self.smpl = None


    @Slot()
    def openFileDialog(self):
        parent = QApplication.activeWindow()

        self.file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "PKL 파일 선택",
            "",
            "Pickle Files (*.pkl)"
        )

        if self.file_path:
            self.fileSelected.emit(True)
            # self.set_pkl_data(file_path)


    @Slot(str)
    def scanningStart(self, message):
        data = json.loads(message)
        SingletonManager.scanning = data['scanning']

    @Slot()
    def pklStart(self):
        # PklManager(self.file_path).start()
        self.file_path = ''

    @Slot(str)
    def send_station_list(self, list):
        # print({"list":list})
        self.stationListUpdated.emit(json.dumps({"list":list}))

    @Slot(str)
    def sendConnection(self, message):
        data = json.loads(message)
        SingletonManager().player_connect_station(data['index'], data['value'])

    @Slot(str)
    def setMixmoStart(self, message):
        data = json.loads(message)
        index = data['index']
        if SingletonManager().player[index] is not None:
            SingletonManager().player[index].check = True

    @Slot(bool)
    def endSensor(self, message):
        print(1213123123123123)
        if message:
            for key, player in SingletonManager().player.items():
                if player is not None:
                    SingletonManager().player[key].stop()

            print(SingletonManager().player)

    @Slot(bool)
    def startCamera(self, message):
        if message and self.smpl is not None:
           self.smpl.camera_send_start = True


    @Slot(bool)
    def endCamera(self, message):
        if message and self.smpl is not None:
           self.smpl.camera_send_start = False


    @Slot(bool)
    def setTpose(self, message):
        if message:
            print(message)
            SingletonManager().all_tpose()




    def send_frame_bone(self, data, finger_value):
        payload = {
            "frameBoneRotation": data,
            "frameFingerRotation": finger_value,
            "udpSwitch": True,
        }

        # Python -> JS 실시간 전송
        self.frameUpdated.emit(json.dumps(payload))

    def send_start_camera(self, smpl):
        self.smpl = smpl
        self.setLoading.emit(False)





