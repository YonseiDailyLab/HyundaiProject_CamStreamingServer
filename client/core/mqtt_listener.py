import logging
import uuid
import time
import json
import paho.mqtt.client as mqtt
import multiprocessing
import config as cfg

class MQTTListener:
    """MQTT 리스너 클래스"""
    
    def __init__(self, ip_queue: multiprocessing.Queue):
        self.ip_queue = ip_queue
        self.client_id = f"discovery-client-{uuid.uuid4()}"
        self.response_topic = f"camera/response/{self.client_id}"
        self.client = None
        self.is_running = False

    def on_connect(self, client, userdata, flags, rc):
        """MQTT 연결 콜백"""
        if rc == 0:
            logging.info("[MQTT] Broker connected")
            # 서버 응답 토픽, command 토픽, 센서 토픽 구독
            topics = [
                (self.response_topic, 0),
                (cfg.MQTT_TOPIC_COMMAND, 0),
                ("sensor/#", 0),  # 모든 센서 토픽 구독
            ]
            client.subscribe(topics)
            logging.info(f"[MQTT] Subscribed topics: {[topic for topic, _ in topics]}")

            # 연결되자마자 discovery 요청 전송
            self.client.publish(cfg.MQTT_TOPIC_REQUEST, self.response_topic)
            logging.info(f"[MQTT] Published discovery request to {cfg.MQTT_TOPIC_REQUEST}: {self.response_topic}")
        else:
            logging.error(f"[MQTT] Connection failed: {rc}")

    def on_message(self, client, userdata, msg):
        """MQTT 메시지 수신 콜백"""
        try:
            payload = msg.payload.decode()
            topic = msg.topic
            
            logging.info(f"[MQTT] Received message on topic '{topic}': {payload}")
            
            if topic == cfg.MQTT_TOPIC_COMMAND:
                # 명령 토픽 처리: payload == start/stop/true/false
                normalized = payload.strip().lower()
                if normalized in ("start", "true", "recording_start"):
                    logging.info("[MQTT] Recording start command received")
                    self.ip_queue.put(("recording_start", None))
                elif normalized in ("stop", "false", "recording_stop"):
                    logging.info("[MQTT] Recording stop command received")
                    self.ip_queue.put(("recording_stop", None))
                else:
                    logging.info(f"[MQTT] Unknown command: {payload}")
            elif topic == self.response_topic:  # 서버로부터의 IP 응답
                if payload:
                    logging.info(f"[MQTT] Server IP received: {payload}")
                    # IP 주소를 큐에 추가
                    self.ip_queue.put(payload)
            elif "camera/response" in topic and payload:  # 다른 클라이언트의 응답도 처리
                logging.info(f"[MQTT] Additional server IP received: {payload}")
                self.ip_queue.put(payload)
            elif topic.startswith("sensor/"):  # 센서 데이터 처리
                logging.debug(f"[MQTT] Sensor data received on topic {topic}")
                try:
                    # 센서 데이터 파싱 및 큐로 전달
                    data = json.loads(payload)
                    self.ip_queue.put(("sensor_data", (topic, data)))
                except json.JSONDecodeError:
                    logging.error(f"[MQTT] Invalid sensor data format: {payload}")
        except Exception as e:
            logging.error(f"[MQTT] Message processing error: {e}")

    def periodic_request(self):
        """주기적 IP 요청"""
        while self.is_running:
            try:
                if self.client and self.client.is_connected():
                    logging.info(f"[MQTT] Discovery request: '{cfg.MQTT_TOPIC_REQUEST}'")
                    self.client.publish(cfg.MQTT_TOPIC_REQUEST, self.response_topic)
                time.sleep(15)
            except Exception as e:
                logging.error(f"[MQTT] Request error: {e}")
                break

    def start(self):
        """MQTT 리스너 시작"""
        try:
            self.client = mqtt.Client(client_id=self.client_id)
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.is_running = True

            # MQTT 클라이언트 디버그 로그 활성화
            self.client.enable_logger()

            logging.info(f"[MQTT] Connecting to broker {cfg.MQTT_BROKER_IP}:{cfg.MQTT_PORT}...")
            self.client.connect(cfg.MQTT_BROKER_IP, cfg.MQTT_PORT, 60)
            
            # MQTT 메인 루프 시작
            self.client.loop_start()
            
            # 요청 전송 루프 시작
            self.periodic_request()
            
            # 메인 스레드 유지
            while self.is_running:
                time.sleep(1)
        except Exception as e:
            logging.error(f"[MQTT] Error: {e}")
        finally:
            self.is_running = False
