# 실시간 스트리밍 서버 README

## 1. 프로젝트 개요
MQTT와 TCP 소켓 통신을 결합한 실시간 카메라 스트리밍 시스템

- **동적 서버 탐색**: MQTT를 통한 자동 서버 IP 발견
- **다중 서버 지원**: 여러 서버 동시 연결 및 관리
- **고품질 영상 스트리밍**: libcamera 기반 실시간 스트리밍
- **자동 녹화 기능**: 분할 녹화 및 명령 기반 제어
- **센서 데이터 수집**: MQTT 센서 데이터 로깅

***

## 2. 프로젝트 구조
```
/
├── server/
│   ├── main.py                # 서버 메인 프로세스 (MQTT/스트림 관리)
│   ├── mqtt_manager.py        # 서비스 탐색 기능 (MQTT)
│   └── stream_server.py       # 영상 스트리밍 기능 (Socket)
│
├── client/
│   ├── main.py                # 클라이언트 메인 애플리케이션
│   └── core/
│       ├── __init__.py        # 패키지 초기화
│       ├── mqtt_listener.py   # MQTT 통신 및 서버 탐색
│       ├── stream_viewer.py   # 스트림 수신 및 표시
│       ├── video_recorder.py  # 영상 녹화 관리
│       └── sensor_logger.py   # 센서 데이터 로깅
│
├── config.py                  # 공통 설정 파일
├── requirements.txt           # 의존성 패키지
├── run_server.sh              # 서버 실행 프로그렘
└── README.md               
```

***

## 3. 전체 시스템 흐름

1. **서버 시작**: server/main.py 실행 시, MQTT 관리자와 스트리밍 서버 두 프로세스 동시 실행

2. **클라이언트 시작**: client/main.py 실행으로 다중 프로세스 기반 클라이언트 시작
   - MQTT 리스너 프로세스: 서버 탐색 및 센서 데이터 수신
   - 메인 프로세스: 다중 서버 연결 관리

3. **서버 탐색**: 클라이언트의 MQTT 리스너가 주기적으로 서버 IP 요청 발행

4. **IP 응답**: 서버의 MQTT 관리자가 요청을 수신하고 자신의 로컬 IP 주소 응답

5. **다중 연결**: 발견된 각 서버마다 독립적인 스트림 뷰어 프로세스 생성

6. **실시간 스트리밍**: 각 뷰어 프로세스가 해당 서버와 독립적으로 연결하여 영상 수신 및 표시

7. **자동 녹화**: MQTT 명령에 따라 모든 연결된 서버의 영상을 동시 녹화/중지

8. **센서 데이터**: 센서 토픽으로 수신되는 데이터를 자동으로 CSV 파일에 저장

***

## 4. 주요 기능

### 4.1. 다중 서버 지원
- 네트워크상의 모든 스트리밍 서버 자동 발견
- 서버별 독립적인 연결 및 스트림 처리
- 서버 추가/제거 시 동적 연결 관리

### 4.2. 영상 녹화 시스템
- **분할 녹화**: 1분 단위로 자동 분할하여 MP4 파일 저장
- **명령 기반 제어**: MQTT 명령으로 전체 서버 동시 녹화 시작/중지
- **서버별 관리**: 각 서버의 영상을 별도 디렉토리에 저장

### 4.3. 센서 데이터 로깅
- MQTT 센서 토픽 자동 구독
- 센서 데이터 실시간 CSV 저장
- 녹화 세션과 동기화된 파일명

### 4.4. 프로세스 관리
- 멀티프로세싱 기반 안정적인 동시 처리
- Ctrl+C 시 모든 프로세스 안전 종료
- 프로세스 상태 모니터링 및 자동 복구

***

## 5. 각 파일 기능 설명
* config.py:
    > MQTT 브로커, 포트, 토픽 등 시스템의 모든 공통 설정 관리
    >
    > 로깅 설정 및 스트리밍 서버 설정 포함

### 서버 측 파일

* server/main.py:
    > 서버의 메인 시작점. multiprocessing을 이용해 MQTT 관리자와 스트리밍 서버를 독립 프로세스로 실행
    >
    > Ctrl+C 입력 시 프로세스 안전 종료 기능 포함

* server/mqtt_manager.py:
    > 서비스 탐색 기능 담당. paho-mqtt 라이브러리 사용
    >
    > command 토픽 구독 및 클라이언트의 IP 요청에 대한 응답 로직 구현

* server/stream_server.py:
    > 실시간 영상 스트리밍 담당. subprocess로 libcamera-vid를 직접 실행하여 고효율 스트림 생성
    >
    > socket 서버를 통해 연결된 다중 클라이언트에게 스레드를 할당하여 영상 프레임 전송

### 클라이언트 측 파일

* client/main.py:
    > 클라이언트의 메인 진입점. 다중 프로세스 관리 및 전체 워크플로우 조정
    >
    > MQTT 리스너, 다중 스트림 뷰어, 센서 데이터 관리를 통합

* client/core/mqtt_listener.py:
    > MQTT 통신 전담. 서버 탐색, 센서 데이터 수신, 명령 처리
    >
    > 주기적 서버 IP 요청 및 다중 서버 응답 관리

* client/core/stream_viewer.py:
    > 개별 서버와의 스트림 연결 및 영상 표시
    >
    > OpenCV 기반 실시간 영상 처리 및 화면 출력

* client/core/video_recorder.py:
    > 영상 녹화 전담. 1분 단위 분할 녹화 및 파일 관리
    >
    > 서버별 독립적인 녹화 세션 관리 (싱글톤 패턴)

* client/core/sensor_logger.py:
    > 센서 데이터 CSV 저장 및 관리
    >
    > 녹화 세션과 동기화된 파일명 체계

***

## 6. 사용법

### 6.1. 서버 실행
```bash
# 서버 디렉토리에서
bash run_server.sh
```

### 6.2. 클라이언트 실행
```bash
# 프로젝트 루트에서
python -m client.main
```

### 6.3. 녹화 제어
MQTT 명령을 통해 녹화를 제어할 수 있음:

```bash
# 녹화 시작
mosquitto_pub -h <MQTT_BROKER_IP> -t "command/rec" -m "start"

# 녹화 중지  
mosquitto_pub -h <MQTT_BROKER_IP> -t "command/rec" -m "stop"
```

***

## 7. 시스템 아키텍처

### 7.1. 현재 구현된 기능
- **다중 서버 동시 접속**: 여러 스트리밍 서버에 동시 연결 가능  
- **독립적 프로세스 관리**: 각 서버마다 별도 프로세스로 안정적 처리  
- **자동 영상 녹화**: MQTT 명령으로 모든 서버 동시 녹화 제어  
- **센서 데이터 수집**: MQTT 센서 데이터 자동 CSV 저장  
- **분할 녹화**: 1분 단위 자동 분할로 파일 관리 최적화  
- **동적 서버 탐색**: 새로운 서버 자동 발견 및 연결  

### 7.2. 기술적 특징
- **멀티프로세싱**: 서버별 독립적인 프로세스로 안정성 확보
- **싱글톤 패턴**: 서버별 VideoRecorder 인스턴스 관리
- **논블로킹 통신**: 비동기적 MQTT 통신 및 명령 처리
- **안전한 종료**: Ctrl+C 시 모든 프로세스 정상 종료

***

## 8. 설정

### 8.1. MQTT 설정 (config.py)
```python
MQTT_BROKER_IP = "192.168.0.235"  # MQTT 브로커 IP
MQTT_PORT = 1883                   # MQTT 포트
MQTT_TOPIC_REQUEST = "command/getIP"  # IP 요청 토픽
MQTT_TOPIC_COMMAND = "command/rec"    # 녹화 명령 토픽
```

### 8.2. 스트리밍 설정
```python
STREAM_HOST = '0.0.0.0'           # 스트리밍 서버 호스트
STREAM_PORT = 8000                # 스트리밍 서버 포트
LIBCAMERA_VID_COMMAND = 'libcamera-vid --inline --nopreview -t 0 --codec mjpeg --width 1920 --height 1080 -o -'
```

***

## 9. 요구사항

### 9.1. 서버 (라즈베리파이)
- Python 3.11+
- libcamera (라즈베리파이 OS 기본 제공)
- paho-mqtt

### 9.2. 클라이언트
- Python 3.11+
- OpenCV (cv2)
- paho-mqtt
- numpy
- pandas

설치 방법:
```bash
// cam_server 라는 이름의 가상환경이 없다면
// conda create -n cam_server python=3.12

conda activate cam_server
pip install -r requirements.txt
```
