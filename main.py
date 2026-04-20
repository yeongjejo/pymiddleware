from protocal.station.udp_station_broadcast_receiver import UDPStationBroadcastReceiver
import subprocess
import time
import math
import json

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl, QObject, Signal, Slot, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebChannel import QWebChannel
import sys

from singleton_manager import SingletonManager

process = None

class WebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        level_map = {
            QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: "INFO",
            QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: "WARN",
            QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: "ERROR",
        }
        level_text = level_map.get(level, "LOG")
        print(f"[JS {level_text}] {sourceID}:{lineNumber} - {message}")
        super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)


class Bridge(QObject):
    frameUpdated = Signal(str)
    logMessage = Signal(str)

    def __init__(self):
        super().__init__()
        self.t = 0.0

    @Slot(str)
    def sendFromJs(self, message):
        data = json.loads(message)
        print("JS에서 받은 데이터:", data)


    # @Slot(result=str)
    # def getInitialData(self):
    #     payload = {
    #         "frameBoneRotation": self.make_test_frame(),
    #         "frameBonePosition": [],
    #         "udpSwitch": True,
    #     }
    #     return json.dumps(payload)

    @Slot(str)
    def sendFrameAck(self, message):
        print("JS -> Python:", message)
        self.logMessage.emit(f"ack received: {message}")

    def make_test_frame(self):
        # boneRefList 길이를 몰라서 넉넉하게 80개 생성
        # 포맷: [w, x, y, z]
        bones = [[1.0, 0.0, 0.0, 0.0] for _ in range(80)]

        # 예시로 몇 개 뼈만 살짝 움직이도록 설정
        angle = math.sin(self.t) * 0.5
        w = math.cos(angle / 2.0)
        x = math.sin(angle / 2.0)

        bones[10] = [w, x, 0.0, 0.0]
        bones[15] = [w, 0.0, x, 0.0]
        bones[20] = [w, 0.0, 0.0, x]

        return bones

    def send_test_frame(self, data, finger_value):
        # print(111)
        self.t += 0.1

        payload = {
            "frameBoneRotation": data,
            "frameFingerRotation": finger_value,
            "udpSwitch": True,
        }

        # Python -> JS 실시간 전송
        self.frameUpdated.emit(json.dumps(payload))
        # self.logMessage.emit("test frame sent")

        # print('전송완')







class WebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        level_map = {
            QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: "INFO",
            QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: "WARN",
            QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: "ERROR",
        }
        level_text = level_map.get(level, "LOG")
        print(f"[JS {level_text}] {sourceID}:{lineNumber} - {message}")

        super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)



def server_stopped():
    if process is not None:
        result = subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print(result.stderr)



    UDPStationBroadcastReceiver().stop()


    print("server stopped")

if __name__ == '__main__':
    UDPStationBroadcastReceiver().start()

    # Front 실행
    project_dir = r"C:\Users\USER\Desktop\4dhmuan-front"
    process = subprocess.Popen(
        ["npm.cmd", "run", "dev", "--", "--host", "0.0.0.0"],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # 프로그램 실행
    app = QApplication(sys.argv)

    view = QWebEngineView()
    page = WebPage(view)
    view.setPage(page)

    view.load(QUrl("http://localhost:5173"))
    view.resize(1200, 800)
    view.show()


    # QWebChannel 연결
    channel = QWebChannel(page)
    bridge = Bridge()
    channel.registerObject("bridge", bridge)
    SingletonManager().bridge = bridge
    page.setWebChannel(channel)

    # # 주기적으로 테스트 데이터 전송
    # timer = QTimer()
    # timer.timeout.connect(bridge.send_test_frame)
    # timer.start(100)   # 100ms마다 전송


    app.aboutToQuit.connect(server_stopped)

     # 프로그램 종료시
    exit_code = app.exec()
    server_stopped()
    sys.exit(exit_code)
