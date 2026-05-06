from cam.live_smpl import LiveSmpl
from protocal.signal_bridge import SignalBridge
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
dev_tools_view = None
dev_tools_page = None

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


def open_devtools(main_page):
    global dev_tools_view, dev_tools_page

    if dev_tools_view is None:
        dev_tools_view = QWebEngineView()
        dev_tools_page = QWebEnginePage(main_page.profile(), dev_tools_view)
        dev_tools_view.setPage(dev_tools_page)

        # 메인 페이지와 개발자 도구 페이지 연결
        main_page.setDevToolsPage(dev_tools_page)

        dev_tools_view.resize(1000, 700)
        dev_tools_view.setWindowTitle("Chrome DevTools")

    dev_tools_view.show()
    dev_tools_view.raise_()
    dev_tools_view.activateWindow()


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
    LiveSmpl().start()

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
    bridge = SignalBridge()
    channel.registerObject("bridge", bridge)
    SingletonManager().bridge = bridge
    page.setWebChannel(channel)

    open_devtools(page)


    app.aboutToQuit.connect(server_stopped)

     # 프로그램 종료시
    exit_code = app.exec()
    server_stopped()
    sys.exit(exit_code)
