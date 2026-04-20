import threading


class Signal(threading.Thread):

    def __init__(self):
        super().__init__()

        self.send_sensor_data = False



