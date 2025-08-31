# server/stream_server.py

import socket
import threading
import subprocess
import shlex
import struct
import logging
import config as cfg

# --- 전역 변수 ---
LATEST_FRAME = None
LOCK = threading.Condition()

def setup_logging():
    """기본 로깅 설정"""
    logging.basicConfig(
        level=cfg.LOG_LEVEL,
        format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def capture_frames(process):
    """libcamera-vid 출력을 읽어 JPEG 프레임 파싱하고 공유 변수에 저장"""
    global LATEST_FRAME
    buffer = b""
    while True:
        try:
            chunk = process.stdout.read(4096)
            if not chunk:
                logging.warning("stdout stream ended. Terminating capture thread.")
                break
            buffer += chunk
            
            a = buffer.find(b'\xff\xd8')
            b = buffer.find(b'\xff\xd9')

            if a != -1 and b != -1:
                jpg = buffer[a:b+2]
                buffer = buffer[b+2:]

                with LOCK:
                    LATEST_FRAME = jpg
                    LOCK.notify_all()
        except Exception as e:
            logging.error(f"Error reading from stdout: {e}")
            break

def monitor_stderr(process):
    """libcamera-vid의 표준 에러 출력 로깅"""
    while True:
        try:
            line_bytes = process.stderr.readline()
            if not line_bytes:
                break
            
            line = line_bytes.decode().strip()

            if "ERROR" in line:
                logging.error(f"[libcamera-vid] {line}")
            elif "WARN" in line:
                logging.warning(f"[libcamera-vid] {line}")
            else:
                logging.info(f"[libcamera-vid] {line}")
        except Exception as e:
            logging.error(f"Error reading from stderr: {e}")
            break

def handle_client(conn, addr):
    """연결된 클라이언트에게 프레임 전송"""
    logging.info(f"New connection from {addr}")
    try:
        while True:
            with LOCK:
                LOCK.wait()
                frame = LATEST_FRAME
            
            if frame is None or len(frame) == 0:
                continue

            try:
                size = len(frame)
                packed_size = struct.pack(">L", size)
                conn.sendall(packed_size)
                conn.sendall(frame)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                logging.warning(f"Connection lost from {addr}")
                break
            except Exception as e:
                logging.error(f"Send error to {addr}: {e}")
                break
    finally:
        logging.info(f"Closing connection for {addr}")
        conn.close()

def start_stream_server():
    """스트리밍 서버의 모든 기능 시작 및 관리"""
    setup_logging()
    
    process = subprocess.Popen(shlex.split(cfg.LIBCAMERA_VID_COMMAND), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logging.info(f"Started libcamera-vid process with command: {cfg.LIBCAMERA_VID_COMMAND}")

    # 캡처 및 에러 모니터링을 위한 백그라운드 스레드 시작
    threading.Thread(target=capture_frames, args=(process,), name="CaptureThread", daemon=True).start()
    threading.Thread(target=monitor_stderr, args=(process,), name="StderrMonitorThread", daemon=True).start()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 소켓 재사용 옵션 설정
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((cfg.STREAM_HOST, cfg.STREAM_PORT))
    server_socket.listen()
    logging.info(f"Server is listening on {cfg.STREAM_HOST}:{cfg.STREAM_PORT}")

    try:
        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(conn, addr), name=f"Client-{addr[0]}", daemon=True).start()
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, shutting down.")
    finally:
        logging.info("Stopping server and processes...")
        process.terminate()
        server_socket.close()

if __name__ == '__main__':
    start_stream_server()