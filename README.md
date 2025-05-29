# <b>Homeassistant Addon for Chinese SR-201 Lan Relay Board</b> </br>

Also here you can find official software and documentation for it : </br>
https://github.com/mamontuka/sr201-ha/tree/main/original_dev_pack

Instalation : </br>
1 - Add this repository to addons (three dots) - https://github.com/mamontuka/sr201-ha </br>
2 - Install this addon </br>
3 - In addon setings setup Lan Relay IP, port (if behind NAT), MQTT settings </br>
4 - Take example below, ajust for self </br>

Homeassistant entities card configuration example : https://github.com/mamontuka/sr201-ha/tree/main/entities_card_example </br>

**UPDATE 1.1 - improving stability, fixes.** </br>

Addon config explanation : </br>

    # Board 1 ID for prefix to entities unique ID, like "sr201_1_rl_1"
    - device_id: sr201_1
    # You have this board IRL ? true - yes, false - SKIP this board
      enabled: true
    # Changeable board name in MQTT anouncement
      friendly_name: SR-201 Board 1
    # Board 1 IP address
      relay_ip: 192.168.0.100
    # Board port, default 6722, but can be changed if you use board behind NAT
      relay_port: 6722
    # How much relays this board have ?
      relay_count: 2
    # Default relays state - printed here relays numbers have NC (normaly connected) wiring, not printed - normaly disconnected.
    # Thats inverting switches in Homeassistant
      inverted_relays:
        - 1
    # relay numbers what act like trigger, instead two position switch
      triggers:
        - 0
    # Board 2 ID for prefix to entities unique ID, like "sr201_2_rl_1"
      - device_id: sr201_2
    # You have this board IRL ? true - yes, false - SKIP this board
      enabled: false
    # Changeable board name in MQTT anouncement
      friendly_name: SR-201 Board 2
    # Board 2 IP address
      relay_ip: 192.168.0.101
    # Board port, default 6722, but can be changed if you use board behind NAT
      relay_port: 6722
    # How much relays this board have ?
      relay_count: 2
    # Default relays state - printed here relays numbers have NC (normaly connected) wiring, not printed - normaly disconnected.
    # Thats inverting switches in Homeassistant
      inverted_relays:
        - 0
    # relay numbers what act like trigger, instead two position switch
      triggers:
        - 1
    # More SR-201 boards can be added below by copying and ajusting 
    # example configurations
