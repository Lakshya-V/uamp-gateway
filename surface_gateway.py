"""
surface_gateway.py
-------------------
Listens for incoming UAMP frames, validates the header (magic bytes +
CRC16 checksum), and routes the frame based on its Type Flag:

    TELEMETRY -> logged only, no reply (loss-tolerant, fire-and-forget)
    COMMAND   -> logged, executed, and ACKed back to the sender
    ACK       -> not expected here (gateway is the "server" side)
    HEARTBEAT -> logged, keeps the link-alive counter fresh

Any frame that fails magic/checksum validation is dropped and logged as
corrupted — this is what forces the sender's retransmission logic to
kick in for COMMAND frames.
"""

import socket
import time

from uamp_protocol import (
    pack_frame,
    unpack_frame,
    TYPE_TELEMETRY,
    TYPE_COMMAND,
    TYPE_ACK,
    TYPE_HEARTBEAT,
    UAMPError,
)

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 5050

# simple in-memory stats for a quick sanity check at shutdown
stats = {
    "telemetry_received": 0,
    "commands_received": 0,
    "acks_sent": 0,
    "corrupted_dropped": 0,
    "unknown_type": 0,
}

# seq numbers we've already ACKed, to avoid double-executing a command
# if a duplicate arrives after the gateway's own ACK was lost
_seen_command_seqs = set()


def handle_telemetry(parsed, addr):
    stats["telemetry_received"] += 1
    reading = parsed["payload_json"] or {}
    print(f"[TELEMETRY] from {addr} seq={parsed['seq']:04d} -> {reading}")


def handle_command(sock, parsed, addr):
    stats["commands_received"] += 1
    seq = parsed["seq"]
    cmd = (parsed["payload_json"] or {}).get("cmd", "UNKNOWN")

    if seq in _seen_command_seqs:
        print(f"[COMMAND ] from {addr} seq={seq} '{cmd}' DUPLICATE - "
              f"re-sending ACK without re-executing")
    else:
        _seen_command_seqs.add(seq)
        print(f"[COMMAND ] from {addr} seq={seq} '{cmd}' -> EXECUTED")

    ack_frame = pack_frame(TYPE_ACK, seq, {"status": "ok", "cmd": cmd})
    sock.sendto(ack_frame, addr)
    stats["acks_sent"] += 1
    print(f"[ACK     ] seq={seq} sent back to {addr}")


def handle_heartbeat(parsed, addr):
    print(f"[HEARTBEAT] from {addr} seq={parsed['seq']:04d}")


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_HOST, LISTEN_PORT))
    print(f"Surface Gateway listening on {LISTEN_HOST}:{LISTEN_PORT}")
    print("-" * 60)

    try:
        while True:
            data, addr = sock.recvfrom(2048)

            try:
                parsed = unpack_frame(data)
            except UAMPError as e:
                stats["corrupted_dropped"] += 1
                print(f"[DROPPED ] frame from {addr} failed validation: {e}")
                continue

            frame_type = parsed["type"]
            if frame_type == TYPE_TELEMETRY:
                handle_telemetry(parsed, addr)
            elif frame_type == TYPE_COMMAND:
                handle_command(sock, parsed, addr)
            elif frame_type == TYPE_HEARTBEAT:
                handle_heartbeat(parsed, addr)
            elif frame_type == TYPE_ACK:
                # Gateway shouldn't normally receive ACKs, but log defensively
                print(f"[ACK     ] unexpected ACK from {addr} seq={parsed['seq']} - ignoring")
            else:
                stats["unknown_type"] += 1
                print(f"[UNKNOWN ] type=0x{frame_type:02X} from {addr} - ignoring")

    except KeyboardInterrupt:
        print("\nSurface Gateway shutting down...")
        print("-" * 60)
        print("Session stats:")
        for k, v in stats.items():
            print(f"  {k:22s}: {v}")
        sock.close()


if __name__ == "__main__":
    main()
