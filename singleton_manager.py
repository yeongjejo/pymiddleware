from protocal.station.udp_station_connection import connect_station
from protocal.station.udp_station_server import UDPServer


class SingletonManager:
    _instance = None # 싱글톤 용도

    station_map = {} # key : 시리얼 | value : 스테이션 ip, 포트
    scanning = False

    bridge = None


    # 싱글톤 설정
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SingletonManager, cls).__new__(cls)
        return cls._instance

    # 탐지된 스테이션 추가
    def add_station(self, serial, station_info):
        self.station_map[serial] = station_info

        # todo 아래부분 추후 삭제 (다른 곳으로 이동)
        # port_num = station_info[1]
        #
        # UDPServer(port_num, self.bridge).start()
        #
        # port6 = (port_num >> 8) & 0xFF
        # port7 = port_num & 0xFF
        # connect_station(station_info[0], port6, port7)






