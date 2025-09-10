# client/main.py

import logging
import multiprocessing
import config as cfg
from client.core import MQTTListener, StreamViewer

def setup_logging(default_level=logging.INFO):
    """로깅 설정"""
    # 기본 로깅 설정
    logging.basicConfig(
        level=default_level,
        format='%(asctime)s - %(levelname)s - [%(processName)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 특정 로거 설정
    for logger_name, level in cfg.LOG_LEVELS.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

def mqtt_listener_process(ip_queue: multiprocessing.Queue):
    """MQTT 리스너 프로세스
    
    Args:
        ip_queue: IP 주소를 전달하는 큐
    """
    mqtt_listener = MQTTListener(ip_queue)
    mqtt_listener.start()

def stream_viewer_process(server_ip: str, cmd_queue: multiprocessing.Queue):
    """스트리밍 프로세스
    
    Args:
        server_ip: 스트리밍 서버 IP
    """
    viewer = StreamViewer(server_ip)
    
    if not viewer.connect():
        return

    try:
        while True:
            # non-blocking check for commands
            try:
                cmd = cmd_queue.get_nowait()
                if cmd.lower() in ("true", "start", "recording_start"):
                    viewer.recorder.start_recording()
                elif cmd.lower() in ("false", "stop", "recording_stop"):
                    viewer.recorder.stop_recording()
            except multiprocessing.queues.Empty:
                pass
            except Exception as e:
                logging.error(f"Command error: {e}")

            if not viewer.process_frame():
                break
    except Exception as e:
        logging.exception(f"[{server_ip}] Stream error")
    finally:
        viewer.cleanup()

def main():
    """메인 함수"""
    setup_logging(cfg.LOG_LEVEL)
    logging.info("Starting client application...")

    # IP 큐 생성
    ip_queue = multiprocessing.Queue()
    active_viewers = {}  # server_ip -> {'proc': Process, 'cmd_q': Queue}

    try:
        # MQTT 리스너 시작
        mqtt_process = multiprocessing.Process(
            target=mqtt_listener_process,
            args=(ip_queue,),
            name="MQTT-Listener"
        )
        mqtt_process.start()

        # IP 큐 모니터링
        while True:
            try:
                data = ip_queue.get()
                logging.info(f"Received data from queue: {data}")
                
                if isinstance(data, tuple):
                    # 녹화 명령 처리
                    command, _ = data
                    if active_viewers:  # 서버가 연결되어 있을 때만 명령 전송
                        for viewer_info in active_viewers.values():
                            try:
                                viewer_info['cmd_q'].put(command)
                                logging.info(f"Sent command '{command}' to viewer")
                            except Exception as e:
                                logging.error(f"Failed to send command to viewer: {e}")
                    else:
                        logging.warning("No active viewers to send command to")
                else:
                    # 새로운 서버 IP 처리
                    server_ip = data
                    
                    # 기존 뷰어가 있는지 확인하고 상태 체크
                    if server_ip in active_viewers:
                        viewer_info = active_viewers[server_ip]
                        if viewer_info['proc'].is_alive():
                            logging.info(f"Viewer for {server_ip} is already running")
                            continue
                        else:
                            # 죽은 프로세스 정리
                            logging.warning(f"Cleaning up dead viewer process for {server_ip}")
                            viewer_info['proc'].join()
                            del active_viewers[server_ip]
                    
                    # 새로운 뷰어 프로세스 시작
                    cmd_q = multiprocessing.Queue()
                    process = multiprocessing.Process(
                        target=stream_viewer_process,
                        args=(server_ip, cmd_q),
                        name=f"Stream-{server_ip}"
                    )
                    process.start()
                    logging.info(f"Started viewer process for {server_ip}")
                    active_viewers[server_ip] = {'proc': process, 'cmd_q': cmd_q}

            except Exception as e:
                logging.exception("Error in main loop")

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received")
    finally:
        # 모든 프로세스 정리
        for info in active_viewers.values():
            try:
                if isinstance(info, dict) and 'proc' in info:
                    proc = info['proc']
                    if proc and proc.is_alive():
                        proc.terminate()
                        proc.join(timeout=5.0)
                        if proc.is_alive():
                            proc.kill()
                            proc.join()
            except Exception as e:
                logging.error(f"Error cleaning up viewer process: {e}")
        
        try:
            if mqtt_process.is_alive():
                mqtt_process.terminate()
                mqtt_process.join(timeout=5.0)
                if mqtt_process.is_alive():
                    mqtt_process.kill()
                    mqtt_process.join()
        except Exception as e:
            logging.error(f"Error cleaning up MQTT process: {e}")

if __name__ == "__main__":
    main()