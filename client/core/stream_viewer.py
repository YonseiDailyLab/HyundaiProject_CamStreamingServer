import cv2
import logging
import socket
import struct
import time
import numpy as np
import config as cfg
from .video_recorder import VideoRecorder

class StreamViewer:
    """스트림 뷰어 클래스"""
    
    def __init__(self, server_ip: str):
        self.server_ip = server_ip
        self.client_socket = None
        self.recorder = VideoRecorder(server_ip)
        self.frame_count = 0  # 프레임 카운터
        self.display_interval = 4  # n프레임마다 화면 갱신

    def receive_all(self, count: int) -> bytes:
        """소켓으로부터 지정된 바이트 수만큼 수신
        
        Args:
            count: 수신할 바이트 수
            
        Returns:
            수신된 데이터
        """
        buf = b''
        while len(buf) < count:
            packet = self.client_socket.recv(count - len(buf))
            if not packet:
                return None
            buf += packet
        return buf

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        if self.client_socket is None:
            return False
        try:
            # 소켓이 여전히 연결되어 있는지 확인
            self.client_socket.getpeername()
            return True
        except:
            return False

    def connect(self) -> bool:
        """서버 연결"""
        if self.is_connected():
            logging.info(f"[{self.server_ip}] Already connected")
            return True
            
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_ip, cfg.STREAM_PORT))
            logging.info(f"[{self.server_ip}] Connected to streaming server")
            return True
        except Exception as e:
            logging.error(f"[{self.server_ip}] Connection failed: {e}")
            return False

    def process_frame(self):
        """프레임 처리"""
        frame_start_time = time.time()
        
        # 프레임 크기 수신
        header_data = self.receive_all(4)
        if not header_data:
            logging.warning(f"[{self.server_ip}] Connection lost")
            return False

        msg_size = struct.unpack('>L', header_data)[0]
        if msg_size == 0:
            return True

        # 프레임 데이터 수신
        jpeg_data = self.receive_all(msg_size)
        if jpeg_data is None:
            logging.warning(f"[{self.server_ip}] Frame recv failed")
            return False

        # JPEG 디코딩 시작
        decode_start = time.time()
        nparr = np.frombuffer(jpeg_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        decode_time = time.time() - decode_start

        if frame is None:
            logging.warning(f"[{self.server_ip}] Frame decode failed")
            return True

        # 프레임 업데이트 시작
        update_start = time.time()
        self.recorder.update_frame(frame)
        update_time = time.time() - update_start
        
        # 화면 표시 (일부 프레임만)
        self.frame_count += 1
        display_time = 0
        if self.frame_count % self.display_interval == 0:
            display_start = time.time()
            cv2.imshow(f'Stream from {self.server_ip}', frame)
            cv2.waitKey(1)
            display_time = time.time() - display_start
        
        # 전체 처리 시간 계산
        total_time = time.time() - frame_start_time
        frame_logger = logging.getLogger('frame_processing')
        if total_time > 0.033:  # 30fps 기준 한 프레임당 33ms
            frame_logger.debug(f"[{self.server_ip}] Frame processing too slow: "
                             f"Total={total_time:.3f}s "
                             f"(Decode={decode_time:.3f}s, "
                             f"Update={update_time:.3f}s, "
                             f"Display={display_time:.3f}s)")
        
        return True

    def handle_command(self, command: str):
        """녹화 명령 처리"""
        normalized = command.lower().strip()
        if normalized in ("start", "true", "recording_start"):
            self.recorder.start_recording()
        elif normalized in ("stop", "false", "recording_stop"):
            self.recorder.stop_recording()

    def cleanup(self):
        """리소스 정리"""
        if self.client_socket:
            self.client_socket.close()
        # OpenCV 창을 확실히 닫기
        cv2.destroyAllWindows()
        cv2.waitKey(1)  # 창 닫기를 처리하기 위한 추가 대기
        # 특정 창만 닫기
        try:
            cv2.destroyWindow(f'Stream from {self.server_ip}')
        except:
            pass
