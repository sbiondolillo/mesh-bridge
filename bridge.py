import datetime
import time
from collections import deque

import pubsub
import meshtastic.serial_interface

BACKBONE_DEV = "COM12"
REGIONAL_DEV = "COM13"

backbone = meshtastic.serial_interface.SerialInterface(devPath=BACKBONE_DEV)
regional = meshtastic.serial_interface.SerialInterface(devPath=REGIONAL_DEV)

seen_packets = deque(maxlen=200)

ALLOWED_PORTNUMS = {"TEXT_MESSAGE_APP", "NODEINFO_APP", "ROUTING_APP"}


def pretty_print_packet(packet, origin_mesh, destination_mesh):
    headers = {
        "Origin Mesh": origin_mesh,
        "Destination Mesh": destination_mesh,
        "From": packet.get("fromId"),
        "To": packet.get("toId"),
        "HopLimit": packet.get("hopLimit"),
        "RxTime": datetime.datetime.fromtimestamp(packet.get("rxTime", 0)).isoformat(),
    }

    print("\n--- Packet ---")
    for k, v in headers.items():
        print(f"{k}: {v}")

    decoded = packet.get("decoded", {})
    text = decoded.get("text")
    payload = decoded.get("payload")
    portnum = decoded.get("portnum")

    print(f"PortNum: {portnum}")
    if text:
        print(f"Text: {text}")
    elif payload:
        print(f"Payload (raw): {payload}")
    else:
        print("No text or payload field present")

    print(f"Decoded dict: {decoded}")
    print(f"Packet keys: {list(packet.keys())}")
    print("--------------\n")


def should_forward(packet):
    pkt_id = packet.get("id") or f"{packet.get('fromId')}-{packet.get('rxTime')}"
    if pkt_id in seen_packets:
        return False
    seen_packets.append(pkt_id)

    portnum = packet.get("decoded", {}).get("portnum")
    return portnum in ALLOWED_PORTNUMS


def handle_packet(packet, interface, origin_mesh, destination_mesh, sender, receiver):
    if getattr(interface, "devPath", None) != sender.devPath:
        return

    if not should_forward(packet):
        return

    decoded = packet.get("decoded", {})
    text = decoded.get("text")
    payload = decoded.get("payload")
    portnum = decoded.get("portnum")
    dest = packet.get("toId")

    pretty_print_packet(packet, origin_mesh, destination_mesh)

    if text and dest:
        receiver.sendText(text, destinationId=dest)
    elif payload and dest:
        receiver.sendData(payload, destinationId=dest, portNum=portnum)


def on_backbone(packet, interface):
    handle_packet(packet, interface, "Backbone", "Regional", backbone, regional)


def on_regional(packet, interface):
    handle_packet(packet, interface, "Regional", "Backbone", regional, backbone)


# Subscribe to events
pubsub.pub.subscribe(on_backbone, "meshtastic.receive")
pubsub.pub.subscribe(on_regional, "meshtastic.receive")

print("Bridge running... press Ctrl+C to stop")
while True:
    time.sleep(1)
