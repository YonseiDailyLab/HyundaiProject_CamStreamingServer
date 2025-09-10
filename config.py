# --- MQTT 설정 ---
MQTT_BROKER_IP = "192.168.0.235"
MQTT_PORT = 1883
MQTT_TOPIC_REQUEST = "commend/getIP"
MQTT_TOPIC_COMMAND = "commend/rec"  # recording commands

# --- 스트리밍 서버 설정 ---
STREAM_HOST = '0.0.0.0'
STREAM_PORT = 8000
# libcamera-vid 명령어 (해상도, 프레임레이트 등 여기서 수정)
LIBCAMERA_VID_COMMAND = 'libcamera-vid --inline --nopreview -t 0 --codec mjpeg --width 1920 --height 1080 -o -'

# --- 로깅 설정 ---
import logging

# 기본 로그 레벨은 INFO로 설정
LOG_LEVEL = logging.INFO

# 특정 로거 설정을 위한 딕셔너리
LOG_LEVELS = {
    'frame_processing': logging.DEBUG,  # 프레임 처리 관련 로그는 DEBUG로
    'main': logging.DEBUG,  # 메인 로직 관련 로그는 DEBUG로
}