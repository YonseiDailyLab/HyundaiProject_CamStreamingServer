# client/main.py

import socket
import cv2
import struct
import numpy as np
import paho.mqtt.client as mqtt
import uuid
import threading
import time
import config as cfg

def get_server_ip_from_mqtt():
    """
    MQTT를 통해 스트리밍 서버의 IP 주소를 받아오는 함수.
    성공하면 IP 주소를, 실패하면 None을 반환합니다.
    """
    # IP 주소를 저장할 변수와 수신 완료를 알릴 이벤트 객체
    mqtt_data = {"server_ip": None}
    ip_received_event = threading.Event()

    def on_connect(client, userdata, flags, rc):
        # 연결 성공 시
        if rc == 0:
            logging.info("MQTT Broker connected successfully.")
            # 2. 자신의 고유 응답 토픽을 구독
            client.subscribe(response_topic)
            logging.info(f"Subscribed to response topic: {response_topic}")

            # 3. 'commend' 토픽으로 자신의 응답 토픽 주소를 보내 IP를 요청
            logging.info(f"Requesting server IP by publishing to '{cfg.MQTT_TOPIC_REQUEST}'...")
            client.publish(cfg.MQTT_TOPIC_REQUEST, response_topic)
        else:
            logging.error(f"MQTT connection failed with code: {rc}")
            ip_received_event.set() # 실패 시 대기 종료

    def on_message(client, userdata, msg):
        # 4. 응답 토픽으로 메시지(서버 IP)가 오면
        server_ip = msg.payload.decode()
        logging.info(f"Received server IP: {server_ip}")
        mqtt_data["server_ip"] = server_ip
        ip_received_event.set() # IP를 받았음을 알리고 대기 종료

    # 1. 고유한 클라이언트 ID와 응답 토픽 생성
    client_id = f"python-mqtt-client-{uuid.uuid4()}"
    response_topic = f"camera/response/{client_id}"

    client = mqtt.Client(client_id=client_id)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(cfg.MQTT_BROKER_IP, cfg.MQTT_PORT, 60)
    except Exception as e:
        logging.error(f"MQTT broker connection failed: {e}")
        return None

    client.loop_start() # 논블로킹으로 MQTT 루프 시작

    # IP 주소를 받을 때까지 최대 10초간 대기
    logging.info("Waiting for server IP response...")
    event_triggered = ip_received_event.wait(timeout=10)

    client.loop_stop() # MQTT 루프 종료
    client.disconnect()

    if not event_triggered:
        logging.error("Failed to receive server IP within the timeout period.")
        return None

    return mqtt_data["server_ip"]

def receive_all(sock, count):
    buf = b''
    while len(buf) < count:
        packet = sock.recv(count - len(buf))
        if not packet:
            return None
        buf += packet
    return buf

def start_stream_client(server_ip):
    """스트리밍 서버 접속 및 데이터 수신"""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((server_ip, cfg.STREAM_PORT))
        logging.info(f"Stream server({server_ip}:{cfg.STREAM_PORT}) connected.")
    except Exception as e:
        logging.error(f"Stream server connection failed: {e}")
        return

    try:
        while True:
            header_data = receive_all(client_socket, 4)
            if not header_data:
                logging.warning("Connection lost with server (header recv failed).")
                break

            msg_size = struct.unpack('>L', header_data)[0]
            if msg_size == 0:
                continue

            frame_data = receive_all(client_socket, msg_size)
            if not frame_data:
                logging.warning("Connection lost with server (payload recv failed).")
                break

            frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)

            if frame is not None:
                cv2.imshow(f"Receiving from {server_ip}", frame)
            else:
                logging.warning(f"Frame decoding failed! (Received size: {msg_size} bytes)")
                continue

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        logging.info("Closing connection.")
        client_socket.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # --- 1단계: MQTT로 서버 IP 찾기 ---
    logging.info("Stage 1: Discovering server IP via MQTT...")
    server_ip = get_server_ip_from_mqtt()

    # --- 2단계: 스트리밍 시작 ---
    if server_ip:
        logging.info(f"Stage 2: Starting video stream from server at {server_ip}")
        start_stream_client(server_ip)
    else:
        logging.error("Could not get server IP. Exiting.")