import threading
import socket
from pathlib import Path

from singleton_manager import SingletonManager


class UDPStationBroadcastReceiver(threading.Thread):
    _instance = None  # 싱글톤 용도

    # 싱글톤 설정
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(UDPStationBroadcastReceiver, cls).__new__(cls)
        return cls._instance

    def __init__(self):

        if getattr(self, "_initialized", False):
            return

        super().__init__(daemon=True)
        self._running = False
        self.singleton_manager = SingletonManager()
        self.ds = None
        self._initialized = True

    def stop(self):
        self._running = False  # 스레드 종료 플래그 설정
        if self.ds is not None:
            try:
                self.ds.close()
            except Exception:
                pass
        self.join()  # 스레드가 종료될 때까지 대기

    def run(self):

        self._running = True
        self.broadcast_receiver()

    def broadcast_receiver(self):
        try:
            port = 65000
            self.ds = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.ds.bind(('', port))

            while self._running:
                if not SingletonManager().scanning:
                    continue
                buffer = bytearray(11)  # 수신할 데이터 사이즈 설정

                data, addr = self.ds.recvfrom(len(buffer))  # 데이터 수신

                # 클라이언트 IP 주소 및 포트 번호 확인
                client_ip = addr[0]
                client_port = addr[1]
                # 아이피 주소 저장
                ip_num = f"{data[2]}.{data[3]}.{data[4]}.{data[5]}"
                # 시리얼 번호 저장
                serial = (data[6] << 8) | data[7]  # byte 값을 int로 변환 후 결합
                # print('serial', serial)
                if serial != 315: #todo 추후 삭제
                    continue

                # print(serial)
                # print(f"IP 번호: {ip_num}, 시리얼: {serial}, Port6: {port6}, Port7: {port7}, 채널: {ch}")
                if self.singleton_manager.station_map.get(serial) is None:
                    port_num = self.find_station_port(serial)
                    # print(format(port_num+serial, 'X'))
                    serial = format(port_num+serial, 'X')

                    # port6 = (port_num >> 8) & 0xFF
                    # port7 = port_num & 0xFF

                    # 채널 정보 저장
                    ch = data[8]
                    self.singleton_manager.add_station(serial, [ip_num, port_num, True])

            self.ds.close()
        except Exception as e:
            print(f"Error1: {e}")

        finally:
            if self.ds is not None:
                try:
                    self.ds.close()
                except Exception:
                    pass
                self.ds = None


    def find_station_port(self, serial):
        mapping = {}

        base_path = Path(__file__).resolve().parent
        file_path = base_path / "nonencryption.txt"

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()  # 탭, 공백 모두 처리 가능
                if len(parts) >= 2:
                    key = int(parts[0])
                    value = int(parts[1])
                    mapping[key] = value

        return mapping.get(serial)  # 없으면 None 반환
