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

def send_tcp_command(ip, port, cmd):
    try:
        with socket.create_connection((ip, port), timeout=2) as s:
            s.sendall(cmd.encode())
            return s.recv(32).decode()
    except Exception as e:
        print(f"[ERROR] TCP command failed: {e}")
        return ""

def get_relay_states(board):
    resp = send_tcp_command(board["relay_ip"], board["relay_port"], "00:0^")
    if not resp or len(resp) < board["relay_count"]:
        print(f"[WARN] Invalid state response from {board['device_id']}: {resp}")
        return {}
    states = {}
    for i in range(board["relay_count"]):
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

        triggers = board.get("triggers", [])
        is_trigger = index in triggers

        cmd = push if is_trigger and state == "ON" else (on if state == "ON" else off)
        resp = send_tcp_command(board["relay_ip"], board["relay_port"], cmd)
        print(f"[CMD] Sent '{cmd}' to {board['device_id']} → {resp}")
    except Exception as e:
        print(f"[ERROR] set_relay: {e}")

def announce_device_and_switches(client, board_config):
    if not board_config.get("enabled", True):
        print(f"[SKIP] Skipping disabled board {board_config['device_id']}")
        return

    friendly_name = board_config.get("friendly_name", f"SR-201 {board_config['device_id']}")

    device_config_topic = f"homeassistant/sr201/{board_config['device_id']}/config"
    payload = {
        "name": friendly_name,
        "unique_id": board_config['device_id'],
        "device": {
            "identifiers": [board_config["device_id"]],
            "name": friendly_name,
            "model": "SR-201",
            "manufacturer": "China-manufactured"
        }
    }
    client.publish(device_config_topic, json.dumps(payload), retain=True)
    print(f"[MQTT] Announced device {board_config['device_id']} as {friendly_name}")

    num_relays = board_config["relay_count"]
    for i in range(num_relays):
        unique_id = f"{board_config['device_id']}_rl_{i+1}"
        config_topic = f"homeassistant/switch/{board_config['device_id']}_rl_{i+1}/config"
        relay_payload = {
            "name": f"RL-{i+1}",
            "object_id": f"{board_config['device_id']}_rl_{i+1}",
            "state_topic": f"homeassistant/sr201/{board_config['device_id']}/relay{i}/state",
            "command_topic": f"homeassistant/sr201/{board_config['device_id']}/relay{i}/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": f"homeassistant/sr201/{board_config['device_id']}/relay{i}/availability",
            "unique_id": unique_id,
            "device": {
                "identifiers": [board_config["device_id"]],
                "name": board_config["friendly_name"],
                "model": "SR-201",
                "manufacturer": "China"
            }
        }

        client.publish(config_topic, json.dumps(relay_payload), retain=True)
        client.subscribe(relay_payload["command_topic"])
        client.publish(relay_payload["state_topic"], "OFF", retain=True)
        client.publish(relay_payload["availability_topic"], "online", retain=True)

        if i in board_config.get("triggers", []):
            print(f"[INFO] Relay {i+1} on {board_config['device_id']} set as trigger")

        print(f"[MQTT] Announced relay {i+1} with unique_id {unique_id} for {board_config['device_id']}")

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected with code {rc}")
    for board in config["relay_boards"]:
        if not board.get("enabled", True):
            continue
        announce_device_and_switches(client, board)

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode().upper()
    print(f"[MQTT] Received {topic}: {payload}")
    if topic.endswith("/set"):
        try:
            board_id = topic.split("/")[2]
            idx = int(topic.split("/")[-2].replace("relay", ""))
            for board in config["relay_boards"]:
                if board["device_id"] == board_id:
                    if idx in board.get("inverted_relays", []):
                        payload = "OFF" if payload == "ON" else "ON"
                    set_relay(board, idx, payload)
                    break
        except Exception as e:
            print(f"[ERROR] MQTT command: {e}")

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
