# server/main.py

import multiprocessing
import logging
import time
import config as cfg
from server.mqtt_manager import start_mqtt_manager
from server.stream_server import start_stream_server

def setup_logging(level=logging.INFO):
    """메인 프로세스 로깅 설정"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - [%(processName)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

if __name__ == "__main__":
    setup_logging(cfg.LOG_LEVEL)
    logging.info("Starting server application...")

    try:
        mqtt_process = multiprocessing.Process(target=start_mqtt_manager, name="MQTT-Manager")
        stream_process = multiprocessing.Process(target=start_stream_server, name="Streaming-Server")

        mqtt_process.start()
        stream_process.start()
        logging.info(f"'{mqtt_process.name}' process (PID: {mqtt_process.pid}) has started.")
        logging.info(f"'{stream_process.name}' process (PID: {stream_process.pid}) has started.")
        logging.info("All server processes are running. Press Ctrl+C to terminate.")

        while mqtt_process.is_alive() and stream_process.is_alive():
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received in main process. Terminating child processes.")
    except Exception as e:
        logging.error(f"An error occurred in the main process: {e}")
    finally:
        logging.info("Terminating processes...")
        if mqtt_process.is_alive():
            mqtt_process.terminate()
            mqtt_process.join() # 프로세스가 완전히 종료될 때까지 대기
        if stream_process.is_alive():
            stream_process.terminate()
            stream_process.join() # 프로세스가 완전히 종료될 때까지 대기
        logging.info("All processes have been terminated.")