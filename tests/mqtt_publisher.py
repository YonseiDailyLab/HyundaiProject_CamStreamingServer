"""Simple MQTT publisher for testing recording commands
Usage:
    PYTHONPATH=. python tests/mqtt_publisher.py <response_topic> <start|stop>

This script publishes 'recording_start' or 'recording_stop' to the given response topic.
"""
import sys
import paho.mqtt.client as mqtt
import config as cfg


def main():
    if len(sys.argv) < 3:
        print("Usage: python tests/mqtt_publisher.py <response_topic> <start|stop>")
        return

    response_topic = sys.argv[1]
    cmd = sys.argv[2]
    payload = 'recording_start' if cmd == 'start' else 'recording_stop'

    client = mqtt.Client()
    client.connect(cfg.MQTT_BROKER_IP, cfg.MQTT_PORT, 60)
    client.loop_start()
    print(f"Publishing '{payload}' to '{response_topic}' on {cfg.MQTT_BROKER_IP}:{cfg.MQTT_PORT}")
    client.publish(response_topic, payload)
    client.loop_stop()
    client.disconnect()

if __name__ == '__main__':
    main()
