"""
auv_sender.py
-------------
Simulates the underwater vehicle (AUV) side of the link.

- Fires TELEMETRY frames continuously (fast, loss-tolerant, no ACK expected).
- Periodically fires COMMAND frames that MUST be acknowledged; if no ACK
  arrives within TIMEOUT seconds, the frame is retransmitted (up to
  MAX_RETRIES times).
- PACKET_LOSS_RATE simulates a noisy underwater/acoustic link by randomly
  "dropping" outgoing command frames before they ever leave the socket —
  this proves the retransmission logic actually works, since the gateway
  never even sees the dropped attempt.
"""

import socket
import threading
import time
import random

from uamp_protocol import (
    pack_frame,
    unpack_frame,
    TYPE_TELEMETRY,
    TYPE_COMMAND,
    TYPE_ACK,
    ChecksumMismatchError,
    InvalidMagicError,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 5050

TELEMETRY_INTERVAL = 0.5      # seconds between telemetry frames
COMMAND_INTERVAL = 4.0        # seconds between command attempts
ACK_TIMEOUT = 1.0             # seconds to wait for an ACK before retrying
MAX_RETRIES = 4

PACKET_LOSS_RATE = 0.15       # simulated link loss for command frames

COMMANDS = [
    "GOTO_WAYPOINT",
    "EMERGENCY_STOP",
    "SURFACE_NOW",
    "HOLD_DEPTH",
]

_running = True


# ---------------------------------------------------------------------------
# Telemetry thread — fire and forget, UDP-style, loss-tolerant
# ---------------------------------------------------------------------------

def telemetry_loop(sock: socket.socket):
    seq = 0
    while _running:
        reading = {
            "depth": round(random.uniform(5.0, 60.0), 2),
            "pitch": round(random.uniform(-15.0, 15.0), 2),
            "roll": round(random.uniform(-15.0, 15.0), 2),
            "sonar": round(random.uniform(0.5, 30.0), 2),
        }
        frame = pack_frame(TYPE_TELEMETRY, seq, reading)
        sock.sendto(frame, (GATEWAY_HOST, GATEWAY_PORT))
        print(f"[TELEMETRY] seq={seq:04d} sent -> {reading}")
        seq += 1
        time.sleep(TELEMETRY_INTERVAL)


# ---------------------------------------------------------------------------
# Command thread — reliable channel with ACK + retransmission
# ---------------------------------------------------------------------------

def command_loop(sock: socket.socket):
    seq = 100000  # separate sequence space from telemetry, easy to spot in logs
    cmd_index = 0

    while _running:
        cmd_name = COMMANDS[cmd_index % len(COMMANDS)]
        cmd_index += 1
        payload = {"cmd": cmd_name, "issued_at": time.time()}
        frame = pack_frame(TYPE_COMMAND, seq, payload)

        acked = False
        for attempt in range(1, MAX_RETRIES + 1):
            if random.random() < PACKET_LOSS_RATE:
                print(f"[COMMAND ] seq={seq} '{cmd_name}' attempt {attempt} "
                      f"LOST IN TRANSIT (simulated link loss)")
            else:
                sock.sendto(frame, (GATEWAY_HOST, GATEWAY_PORT))
                print(f"[COMMAND ] seq={seq} '{cmd_name}' attempt {attempt} sent")

            sock.settimeout(ACK_TIMEOUT)
            try:
                data, _addr = sock.recvfrom(2048)
                parsed = unpack_frame(data)
                if parsed["type"] == TYPE_ACK and parsed["seq"] == seq:
                    print(f"[ACK     ] seq={seq} confirmed by gateway "
                          f"(after {attempt} attempt(s))")
                    acked = True
                    break
                else:
                    print(f"[COMMAND ] seq={seq} got unexpected frame "
                          f"(type={parsed['type_name']}, seq={parsed['seq']}), ignoring")
            except socket.timeout:
                print(f"[COMMAND ] seq={seq} '{cmd_name}' ACK timeout "
                      f"({ACK_TIMEOUT}s) - retransmitting" if attempt < MAX_RETRIES
                      else f"[COMMAND ] seq={seq} '{cmd_name}' ACK timeout - giving up")
            except (ChecksumMismatchError, InvalidMagicError) as e:
                print(f"[COMMAND ] seq={seq} received corrupted reply: {e}")

        if not acked:
            print(f"[COMMAND ] seq={seq} '{cmd_name}' FAILED after {MAX_RETRIES} attempts")

        seq += 1
        time.sleep(COMMAND_INTERVAL)

    sock.settimeout(None)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print(f"AUV Sender starting -> target gateway {GATEWAY_HOST}:{GATEWAY_PORT}")
    print(f"  telemetry interval : {TELEMETRY_INTERVAL}s")
    print(f"  command interval   : {COMMAND_INTERVAL}s")
    print(f"  simulated loss rate: {PACKET_LOSS_RATE * 100:.0f}%")
    print("-" * 60)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    t1 = threading.Thread(target=telemetry_loop, args=(sock,), daemon=True)
    t2 = threading.Thread(target=command_loop, args=(sock,), daemon=True)
    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        global _running
        _running = False
        print("\nAUV Sender shutting down...")
        sock.close()


if __name__ == "__main__":
    main()
