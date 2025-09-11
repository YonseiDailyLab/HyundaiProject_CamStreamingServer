# client/core/sensor_logger.py

import os
import json
import time
import logging
import pandas as pd

class SensorDataLogger:
    def __init__(self):
        self.base_dir = os.path.join("Data", "sensors")
        os.makedirs(self.base_dir, exist_ok=True)
        self.columns = ['timestamp', 'mp905', 'mp901', 'mp801', 'sgp30', 'fermion', 'ens160']
        self.active_recordings = {}  # topic -> (start_time, temp_file_path)
        self.is_recording = False

    def get_topic_dir(self, topic):
        """토픽별 디렉토리 경로 반환"""
        # 토픽 이름에서 sensor/ 제거하고 경로 생성
        topic_name = topic.replace('sensor/', '')
        topic_dir = os.path.join(self.base_dir, topic_name)
        os.makedirs(topic_dir, exist_ok=True)
        return topic_dir

    def start_recording(self):
        """센서 데이터 기록 시작"""
        self.is_recording = True
        start_time = int(time.time() * 1000)  # 밀리초 단위
        
        for topic in list(self.active_recordings.keys()):
            self.stop_recording_topic(topic)
            
        logging.info("[Sensor] Started sensor data recording")
        return start_time

    def stop_recording(self):
        """센서 데이터 기록 종료"""
        self.is_recording = False
        end_time = int(time.time() * 1000)  # 밀리초 단위
        
        # 모든 활성 토픽의 기록 종료
        for topic in list(self.active_recordings.keys()):
            self.stop_recording_topic(topic)
            
        logging.info("[Sensor] Stopped sensor data recording")
        return end_time

    def get_temp_path(self, topic):
        """임시 CSV 파일 경로 반환"""
        topic_dir = self.get_topic_dir(topic)
        return os.path.join(topic_dir, "temp_recording.csv")

    def save_sensor_data(self, topic, data):
        """토픽별로 센서 데이터를 CSV에 저장"""
        if not self.is_recording:
            logging.debug(f"[Sensor] Skipping data from {topic} (not recording)")
            return
            
        timestamp = int(time.time() * 1000)  # 밀리초 단위의 Unix timestamp
        
        # 데이터 프레임 생성
        row_data = {
            'timestamp': timestamp,
            'mp905': data.get('mp905', None),
            'mp901': data.get('mp901', None),
            'mp801': data.get('mp801', None),
            'sgp30': data.get('sgp30', None),
            'fermion': data.get('fermion', None),
            'ens160': data.get('ens160', None)
        }
        
        df = pd.DataFrame([row_data])
        
        # 토픽에 대한 recording 세션이 없으면 새로 생성
        if topic not in self.active_recordings:
            temp_path = self.get_temp_path(topic)
            df.to_csv(temp_path, index=False, columns=self.columns)
            self.active_recordings[topic] = (timestamp, temp_path)
            logging.info(f"[Sensor] Started recording for topic '{topic}'")
        else:
            # 기존 파일에 데이터 추가
            _, temp_path = self.active_recordings[topic]
            df.to_csv(temp_path, mode='a', header=False, index=False, columns=self.columns)

    def stop_recording_topic(self, topic):
        """특정 토픽의 기록 종료 및 파일 이름 변경"""
        if topic in self.active_recordings:
            start_time, temp_path = self.active_recordings[topic]
            end_time = int(time.time() * 1000)
            
            if os.path.exists(temp_path):
                topic_dir = self.get_topic_dir(topic)
                # 시작-종료 시간 포맷으로 파일명 생성
                new_filename = f"{start_time}-{end_time}.csv"
                new_path = os.path.join(topic_dir, new_filename)
                
                os.rename(temp_path, new_path)
                logging.info(f"[Sensor] Renamed recording file for topic '{topic}' to {new_filename}")
            
            del self.active_recordings[topic]
