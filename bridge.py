import meshtastic.serial_interface
import pubsub
import time
import datetime
from collections import deque

backbone = meshtastic.serial_interface.SerialInterface(devPath='COM12')
regional = meshtastic.serial_interface.SerialInterface(devPath='COM13')

seen_packets = deque(maxlen=200)

def pretty_print_packet(packet, source_label):
    headers = {
        "Source": source_label,
        "From": packet.get("fromId"),
        "To": packet.get("toId"),
        "HopLimit": packet.get("hopLimit"),
        "RxTime": datetime.datetime.fromtimestamp(packet.get("rxTime", 0)).isoformat()
    }
    text = packet.get("decoded", {}).get("text")

    print("\n--- Packet ---")    
    if text:
        for k, v in headers.items():
            print(f"{k}: {v}")
        print(f"Message: {text}")
    else:
        print("Non‑text packet ignored")
    print("--------------\n")

def should_forward(packet):
    pkt_id = packet.get("id") or f"{packet.get('fromId')}-{packet.get('rxTime')}"
    if pkt_id in seen_packets:
        return False
    seen_packets.append(pkt_id)
    return True

def on_backbone(packet, interface):
    if interface != backbone:
        return  # ignore packets not from backbone
    pretty_print_packet(packet, "Backbone")
    text = packet.get("decoded", {}).get("text")
    if text and should_forward(packet):
        regional.sendText(text, destinationId="^all")

def on_regional(packet, interface):
    if interface != regional:
        return  # ignore packets not from regional
    pretty_print_packet(packet, "Regional")
    text = packet.get("decoded", {}).get("text")
    if text and should_forward(packet):
        backbone.sendText(text, destinationId="^all")

# Subscribe to backbone node events
pubsub.pub.subscribe(on_backbone, f"meshtastic.receive")

# Subscribe to regional node events
pubsub.pub.subscribe(on_regional, f"meshtastic.receive")

print("Bridge running with deduplication... press Ctrl+C to stop")
while True:
    time.sleep(1)
