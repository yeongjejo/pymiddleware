import socket

def connect_station(ip, port6, port7):
    try:
        # 내PC 아이피 주소 가져오기
        local_ip = socket.gethostbyname(socket.gethostname()).split('.')

        # UDP 소켓 생성
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(local_ip)

        # 송신할 데이터 설정
        send_data = bytearray(10)
        send_data[0] = 0xFA
        send_data[1] = 0xEA
        send_data[2] = (int(local_ip[0])) & 0xFF  # IP 주소
        send_data[3] = (int(local_ip[1])) & 0xFF
        send_data[4] = (int(local_ip[2])) & 0xFF
        send_data[5] = (int(local_ip[3])) & 0xFF
        send_data[6] = port6  # 포트 번호
        send_data[7] = port7
        send_data[8] = 0xFB
        send_data[9] = 0xFF

        # IP 주소와 포트 설정
        server_address = (ip, 65000)
        # 데이터 전송
        sock.sendto(send_data, server_address)

    except Exception as e:
        print(f"Error2: {e}")

