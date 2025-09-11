import os
import cv2
import time
import logging
import threading
import numpy as np
from datetime import datetime

class VideoRecorder:
    """비디오 녹화를 담당하는 클래스
    
    실시간 스트리밍 영상을 MP4로 저장하며, 1분 단위로 분할 저장합니다.
    각 영상은 Data/<서버IP>/ 디렉토리에 YYYYMMDD_HHMMSS.mp4 형식으로 저장됩니다.
    
    Attributes:
        server_ip (str): 서버 IP 주소
        is_recording (bool): 현재 녹화 상태
        recording_thread (threading.Thread): 녹화 처리 스레드
        writer (cv2.VideoWriter): 비디오 writer 객체
        start_time (float): 현재 파일 녹화 시작 시간
        frame (numpy.ndarray): 최신 프레임 데이터
        frame_count (int): 현재 파일의 프레임 수
        last_frame_time (float): 마지막 프레임 처리 시간
    """
    
    _instances = {}
    
    def __new__(cls, server_ip):
        """서버 IP당 하나의 인스턴스만 생성"""
        if server_ip not in cls._instances:
            cls._instances[server_ip] = super(VideoRecorder, cls).__new__(cls)
        return cls._instances[server_ip]
    
    def __init__(self, server_ip):
        """VideoRecorder 초기화
        
        Args:
            server_ip (str): 녹화할 스트리밍 서버의 IP 주소
        """
        if hasattr(self, 'initialized'):
            return
            
        self.server_ip = server_ip
        self.is_recording = False
        self.recording_thread = None
        self.writer = None
        self.start_time = None
        self.frame = None
        self.lock = threading.Lock()
        self.observers = []
        self.frame_count = 0
        self.last_frame_time = None
        self.initialized = True

    def add_observer(self, observer):
        """상태 변경을 감시할 옵저버 추가"""
        self.observers.append(observer)
    
    def remove_observer(self, observer):
        """등록된 옵저버 제거"""
        self.observers.remove(observer)
    
    def _notify_observers(self):
        """모든 옵저버에게 상태 변경 알림"""
        for observer in self.observers:
            observer.notify_recording_state(self.is_recording, self.server_ip)

    def get_recording_directory(self) -> str:
        """녹화 파일 저장 디렉토리 생성 및 경로 반환
        
        Returns:
            str: 생성된 디렉토리 경로
            
        Note:
            디렉토리는 Data/cam/<서버IP>/ 형식으로 생성됩니다.
        """
        recording_dir = os.path.join("Data", "cam", self.server_ip)
        os.makedirs(recording_dir, exist_ok=True)
        return recording_dir

    def create_writer(self):
        """새로운 VideoWriter 객체 생성
        
        Returns:
            cv2.VideoWriter: 생성된 writer 객체
            None: 프레임이 없는 경우
            
        Note:
            파일명은 YYYYMMDD_HHMMSS.mp4 형식으로 생성됩니다.
        """
        recording_dir = self.get_recording_directory()
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        microseconds = now.microsecond // 1000  # 밀리초로 변환
        video_path = os.path.join(recording_dir, f"{timestamp}.{microseconds:03d}.mp4")
        
        with self.lock:
            frame = self.frame

        if frame is not None:
            height, width = frame.shape[:2]
            writer = cv2.VideoWriter(
                video_path,
                cv2.VideoWriter_fourcc(*'mp4v'),
                30.0,  # 목표 fps
                (width, height)
            )
            if not writer.isOpened():
                raise IOError(f"Failed to create video writer for {video_path}")
            
            self.start_time = time.time()
            self.frame_count = 0
            self.last_frame_time = self.start_time
            logging.info(f"[{self.server_ip}] Created new video file: {video_path}")
            return writer
        return None

    def _close_writer(self):
        """현재 VideoWriter를 안전하게 종료하고 파일명을 시작-종료 시간으로 변경"""
        if self.writer is not None:
            try:
                # 현재 파일의 실제 fps 계산 및 로깅
                if self.frame_count > 0:
                    end_time = time.time()
                    duration = end_time - self.start_time
                    fps = self.frame_count / duration
                    
                    # 기존 파일명 찾기
                    recording_dir = self.get_recording_directory()
                    current_filename = None
                    for file in os.listdir(recording_dir):
                        if file.endswith(".mp4"):
                            file_path = os.path.join(recording_dir, file)
                            stat = os.stat(file_path)
                            # 가장 최근에 수정된 파일 찾기
                            if stat.st_mtime >= self.start_time:
                                current_filename = file
                                break
                    
                    if current_filename:
                        # 새 파일명 생성 (Unix 타임스탬프 형식, 밀리초 포함)
                        start_ms = int(self.start_time * 1000)
                        end_ms = int(end_time * 1000)
                        new_filename = f"{start_ms}-{end_ms}.mp4"
                        old_path = os.path.join(recording_dir, current_filename)
                        new_path = os.path.join(recording_dir, new_filename)
                        
                        # 파일명 변경
                        self.writer.release()
                        os.rename(old_path, new_path)
                        logging.info(f"[{self.server_ip}] Renamed video file to: {new_filename}")
                        logging.info(f"[{self.server_ip}] Recording statistics - Duration: {duration:.1f}s, "
                                   f"Frames: {self.frame_count}, FPS: {fps:.1f}")
                    else:
                        self.writer.release()
                        logging.warning(f"[{self.server_ip}] Could not find current recording file to rename")
                else:
                    self.writer.release()
            except Exception as e:
                logging.error(f"[{self.server_ip}] Error closing video writer: {e}")
            finally:
                self.writer = None

    def _process_frame(self):
        """현재 프레임을 파일에 기록
        
        Returns:
            bool: 프레임 처리 성공 여부
        """
        with self.lock:
            frame = self.frame
            
        if frame is not None and self.writer is not None:
            try:
                start_time = time.time()
                self.writer.write(frame)
                process_time = time.time() - start_time
                
                # 프레임 처리 시간이 너무 긴 경우 경고
                if process_time > 0.033:  # 30fps 기준 한 프레임당 시간 (1/30초)
                    logging.warning(f"[{self.server_ip}] Frame processing took {process_time:.3f}s")
                return True
            except Exception as e:
                logging.error(f"[{self.server_ip}] Error writing video frame: {e}")
        return False

    def recording_thread_function(self):
        """녹화 스레드 메인 함수"""
        TARGET_FPS = 30
        target_frame_time = 1.0 / TARGET_FPS
        stats_interval = 5.0  # 통계 출력 간격 (초)
        last_stats_time = time.time()
        expected_frames = 0
        next_frame_time = time.time()  # 다음 프레임 처리 시작 시간
        
        try:
            while self.is_recording:
                current_time = time.time()
                
                try:
                    # 파일이 없는 경우에만 새로 생성
                    if self.writer is None:
                        self.writer = self.create_writer()
                        next_frame_time = current_time  # 녹화 시작 시간으로 초기화
                    
                    # 정확한 30fps를 위한 타이밍 제어
                    sleep_time = next_frame_time - current_time
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    
                    # 프레임 처리 시작
                    frame_start = time.time()
                    if self._process_frame():
                        self.frame_count += 1
                        expected_frames += 1
                        
                        # 다음 프레임 시간 계산 (드리프트 방지를 위해 이전 시간 기준)
                        next_frame_time += target_frame_time
                        
                        # 만약 처리가 너무 늦어져서 next_frame_time이 현재보다 과거가 되면 리셋
                        if next_frame_time < time.time():
                            logging.warning(f"[{self.server_ip}] Frame timing reset due to processing delays")
                            next_frame_time = time.time() + target_frame_time
                        
                        # 주기적으로 성능 통계 출력
                        if current_time - last_stats_time >= stats_interval:
                            duration = current_time - last_stats_time
                            expected = int(duration * TARGET_FPS)
                            actual = expected_frames
                            fps = actual / duration
                            logging.info(f"[{self.server_ip}] Recording stats:"
                                       f" FPS={fps:.1f},"
                                       f" Expected={expected},"
                                       f" Actual={actual},"
                                       f" Dropped={expected-actual}")
                            last_stats_time = current_time
                            expected_frames = 0
                        
                        # 프레임 처리 시간 모니터링
                        frame_process_time = time.time() - frame_start
                        if frame_process_time > target_frame_time:
                            logging.warning(f"[{self.server_ip}] Frame processing too slow:"
                                          f" took {frame_process_time:.3f}s"
                                          f" (target: {target_frame_time:.3f}s)")
                        
                        self.last_frame_time = time.time()
                    
                except Exception as e:
                    logging.error(f"[{self.server_ip}] Recording error: {e}")
                    self._close_writer()
                    time.sleep(0.1)  # 에러 발생 시 잠시 대기
                
        finally:
            self._close_writer()
            logging.info(f"[{self.server_ip}] Recording thread terminated")

    def start_recording(self):
        """녹화 시작"""
        if not self.is_recording:
            self.is_recording = True
            self.recording_thread = threading.Thread(
                target=self.recording_thread_function,
                name=f"Recording-{self.server_ip}"
            )
            self.recording_thread.start()
            logging.info(f"[{self.server_ip}] Started recording")
            self._notify_observers()

    def stop_recording(self):
        """녹화 정지"""
        if self.is_recording:
            self.is_recording = False
            if self.recording_thread is not None:
                self.recording_thread.join()
                self.recording_thread = None
            logging.info(f"[{self.server_ip}] Stopped recording")
            self._notify_observers()

    def update_frame(self, frame: np.ndarray):
        """새로운 프레임 데이터 업데이트
        
        Args:
            frame (numpy.ndarray): 업데이트할 프레임 데이터
        """
        with self.lock:
            self.frame = frame.copy()  # 프레임 데이터 복사본 저장