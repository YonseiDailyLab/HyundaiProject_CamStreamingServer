import paho.mqtt.client as mqtt
import socket
import logging
import config as cfg

def setup_logging():
    """기본 로깅 설정"""
    logging.basicConfig(
        level=cfg.LOG_LEVEL,
        format='%(asctime)s - %(levelname)s - [%(processName)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def get_ip_address():
    """서버의 로컬 IP 주소 찾기"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((cfg.MQTT_BROKER_IP, 1))
        IP = s.getsockname()[0]
    except Exception as e:
        logging.error(f"Failed to find local IP address: {e}")
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def on_connect(client, userdata, flags, rc):
    """브로커 연결 콜백 함수"""
    if rc == 0:
        logging.info("Successfully connected to MQTT broker.")
        client.subscribe(cfg.MQTT_TOPIC_REQUEST)
        logging.info(f"Subscribed to topic: '{cfg.MQTT_TOPIC_REQUEST}'")
    else:
        logging.error(f"Failed to connect to broker with result code: {rc}")

def on_message(client, userdata, msg):
    """메시지 수신 콜백 함수"""
    try:
        response_topic = msg.payload.decode()
        logging.info(f"Received IP address request. Response topic: {response_topic}")
        
        server_ip = get_ip_address()
        logging.info(f"Server IP identified: {server_ip}. Publishing to '{response_topic}'.")
        
        # 추출한 응답 토픽으로 서버 IP 주소를 발행
        client.publish(response_topic, server_ip)
    except Exception as e:
        logging.error(f"Error processing message: {e}")

def start_mqtt_manager():
    """MQTT 관리자 프로세스를 시작"""
    setup_logging()
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        logging.info(f"Attempting to connect to MQTT broker at {cfg.MQTT_BROKER_IP}:{cfg.MQTT_PORT}...")
        client.connect(cfg.MQTT_BROKER_IP, cfg.MQTT_PORT, 60)
        
        # 네트워크 트래픽을 처리하고, 재연결 등을 관리하는 블로킹 루프
        client.loop_forever()

    except ConnectionRefusedError:
        logging.error("Broker connection refused. Check if the broker is running and the IP/port are correct.")
    except socket.gaierror:
        logging.error(f"Hostname could not be resolved: {cfg.MQTT_BROKER_IP}. Check the address in config.py.")
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, shutting down MQTT manager.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        logging.info("Disconnecting MQTT client.")
        client.disconnect()

if __name__ == '__main__':
    start_mqtt_manager()