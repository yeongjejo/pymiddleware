import threading
import json

from PySide6.QtCore import Signal, Slot, QObject, QTimer, QTimerEvent
from PySide6.QtWidgets import QFileDialog, QApplication

from protocal.station.pkl_manager import PklManager
from singleton_manager import SingletonManager

import joblib
import numpy as np
from scipy.spatial.transform import Rotation as R

import time


class SignalBridge(QObject):
    frameUpdated = Signal(str)
    pklUpdated = Signal(str)
    fileSelected = Signal(bool)

    file_path = ''

    def __init__(self):
        super().__init__()


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

        print(1)

        PklManager(self.file_path).start()

        print(2)
        self.file_path = ''




    def send_frame_bone(self, data, finger_value):
        payload = {
            "frameBoneRotation": data,
            "frameFingerRotation": finger_value,
            "udpSwitch": True,
        }

        # Python -> JS 실시간 전송
        self.frameUpdated.emit(json.dumps(payload))


