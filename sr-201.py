#!/usr/bin/env python3
import os
import json
import time
import socket
import yaml
import paho.mqtt.client as mqtt
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

def load_config():
    if os.path.exists("/data/options.json"):
        print("[CONFIG] Loading from /data/options.json")
        with open("/data/options.json", "r") as f:
            return json.load(f)
    elif os.path.exists("config.yaml"):
        print("[CONFIG] Loading from config.yaml")
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f).get("options", {})
    else:
        raise FileNotFoundError("No config file found")

config = load_config()

MQTT_BROKER   = config["mqtt_broker"]
MQTT_PORT     = config.get("mqtt_port", 1883)
MQTT_USERNAME = config.get("mqtt_username")
MQTT_PASSWORD = config.get("mqtt_password")
POLL_INTERVAL = config.get("relay_poll_interval", 2)

def send_tcp_command(ip, port, cmd, retries=3):
    for attempt in range(retries):
        try:
            with socket.create_connection((ip, port), timeout=5) as s:
                s.sendall(cmd.encode())
                data = s.recv(32).decode().strip()
                if data:
                    return data
        except Exception as e:
            print(f"[ERROR] TCP command to {ip}:{port} failed on attempt {attempt+1}: {e}")
        time.sleep(1)
    return ""

def get_relay_states(board):
    resp = send_tcp_command(board["relay_ip"], board["relay_port"], "00:0^")
    relay_count = board["relay_count"]

    if not resp or len(resp) < relay_count:
        print(f"[WARN] [{board['device_id']}] Invalid or empty response: '{resp}'")
        return {}

    states = {}
    for i in range(relay_count):
        raw = resp[i]
        state = "ON" if raw == "1" else "OFF"
        if i in board.get("inverted_relays", []):
            state = "OFF" if state == "ON" else "ON"
        states[i] = state
    return states

def set_relay(board, index, state):
    try:
        on = f"1{index+1}:0"
        off = f"2{index+1}:0"
        push = f"1{index+1}:1"

        is_trigger = index in board.get("triggers", [])
        cmd = push if is_trigger and state == "ON" else (on if state == "ON" else off)

        resp = send_tcp_command(board["relay_ip"], board["relay_port"], cmd)
        print(f"[CMD] [{board['device_id']}] Sent '{cmd}' → Response: {resp or 'No response'}")
    except Exception as e:
        print(f"[ERROR] set_relay for {board['device_id']} relay {index}: {e}")

def announce_device_and_switches(client, board):
    if not board.get("enabled", True):
        print(f"[SKIP] Skipping disabled board {board['device_id']}")
        return

    friendly_name = board.get("friendly_name", f"SR-201 {board['device_id']}")
    num_relays = board["relay_count"]

    device_info = {
        "identifiers": [board["device_id"]],
        "name": friendly_name,
        "model": "SR-201",
        "manufacturer": "China-manufactured"
    }

    for i in range(num_relays):
        relay_id = f"{board['device_id']}_rl_{i+1}"
        config_topic = f"homeassistant/switch/{relay_id}/config"
        relay_payload = {
            "name": f"{friendly_name} RL-{i+1}",
            "object_id": relay_id,
            "state_topic": f"homeassistant/sr201/{board['device_id']}/relay{i}/state",
            "command_topic": f"homeassistant/sr201/{board['device_id']}/relay{i}/set",
            "availability_topic": f"homeassistant/sr201/{board['device_id']}/relay{i}/availability",
            "payload_on": "ON",
            "payload_off": "OFF",
            "unique_id": relay_id,
            "device": device_info
        }
        client.publish(config_topic, json.dumps(relay_payload), retain=True)
        client.subscribe(relay_payload["command_topic"])
        client.publish(relay_payload["availability_topic"], "online", retain=True)
        client.publish(relay_payload["state_topic"], "OFF", retain=True)
        print(f"[MQTT] Announced relay {i+1} on {board['device_id']}")

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected with code {rc}")
    client.publish("homeassistant/sr201/bridge/status", "online", retain=True)
    for board in config["relay_boards"]:
        announce_device_and_switches(client, board)

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode().strip().upper()
    print(f"[MQTT] Received {topic}: {payload}")

    if topic.endswith("/set"):
        try:
            parts = topic.split("/")
            board_id = parts[2]
            idx = int(parts[3].replace("relay", ""))
            for board in config["relay_boards"]:
                if board["device_id"] == board_id:
                    if idx in board.get("inverted_relays", []):
                        payload = "OFF" if payload == "ON" else "ON"
                    set_relay(board, idx, payload)
                    break
        except Exception as e:
            print(f"[ERROR] MQTT handling failed: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

if MQTT_USERNAME and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

client.will_set("homeassistant/sr201/bridge/status", "offline", retain=True)
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

try:
    while True:
        for board in config["relay_boards"]:
            if not board.get("enabled", True):
                continue
            states = get_relay_states(board)
            for i, state in states.items():
                client.publish(f"homeassistant/sr201/{board['device_id']}/relay{i}/state", state, retain=True)
        time.sleep(POLL_INTERVAL)
except KeyboardInterrupt:
    print("Stopping...")
finally:
    client.publish("homeassistant/sr201/bridge/status", "offline", retain=True)
    client.loop_stop()
