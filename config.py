# --- MQTT 설정 ---
MQTT_BROKER_IP = "192.168.0.235"
MQTT_PORT = 1883
MQTT_TOPIC_REQUEST = "commend"

# --- 스트리밍 서버 설정 ---
STREAM_HOST = '0.0.0.0'
STREAM_PORT = 8000
# libcamera-vid 명령어 (해상도, 프레임레이트 등 여기서 수정)
LIBCAMERA_VID_COMMAND = 'libcamera-vid --inline --nopreview -t 0 --codec mjpeg --width 1920 --height 1080 -o -'

# --- 로깅 설정 ---
import logging
LOG_LEVEL = logging.INFO