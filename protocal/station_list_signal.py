import threading


class StationListSignal(threading.Thread):

    def __init__(self):
        super().__init__()

        self.send_sensor_data = False




