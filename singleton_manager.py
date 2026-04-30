from protocal.station.udp_station_connection import connect_station
from protocal.station.udp_station_server import UDPServer


class SingletonManager:
    _instance = None # 싱글톤 용도

    bridge = None

    station_map = {} # key : 시리얼 | value : 스테이션 ip, 포트
    # scanning = True #테스트용
    scanning = False

    player = {
        0 : None,
        1 : None,
        2 : None,
        3 : None,
        4 : None,
        5 : None,
        6 : None,
        7 : None,
    }

    # 싱글톤 설정
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SingletonManager, cls).__new__(cls)
        return cls._instance

    # 탐지된 스테이션 추가
    def add_station(self, serial, station_info):
        self.station_map[serial] = station_info
        self.bridge.send_station_list(list(self.station_map.keys()))


    def player_connect_station(self, index, serial):
        port_num = self.station_map[serial][1]

        self.player[index] = UDPServer(port_num, self.bridge)
        if self.player[index] is not None:
            self.player[index].start()

        port6 = (port_num >> 8) & 0xFF
        port7 = port_num & 0xFF
        connect_station(self.station_map[serial][0], port6, port7)






