"""
auv_sender.py
-------------
Simulates the underwater vehicle (AUV) side of the link.

- Fires TELEMETRY frames continuously over UDP (fast, loss-tolerant).
- Periodically fires COMMAND frames requiring ACKs (with retransmissions).
- Simulates packet loss using PACKET_LOSS_RATE.
"""

import socket
import threading
import time
import json
import random

import uamp_protocol as uamp

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 5000  # Matches surface_gateway.py port

TELEMETRY_INTERVAL = 0.5   # Seconds between telemetry frames
COMMAND_INTERVAL = 4.0     # Seconds between command attempts
ACK_TIMEOUT = 1.0          # Seconds to wait for an ACK
MAX_RETRIES = 4

PACKET_LOSS_RATE = 0.15    # 15% simulated acoustic link loss

COMMANDS = [
    "GOTO_WAYPOINT",
    "EMERGENCY_STOP",
    "SURFACE_NOW",
    "HOLD_DEPTH",
]

_running = True


# ---------------------------------------------------------------------------
# Telemetry Loop — Fire-and-forget UDP
# ---------------------------------------------------------------------------
def telemetry_loop():
    # Separate socket for telemetry to avoid socket lock contention
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 0
    
    while _running:
        reading = {
            "depth": round(random.uniform(5.0, 60.0), 2),
            "pitch": round(random.uniform(-15.0, 15.0), 2),
            "roll": round(random.uniform(-15.0, 15.0), 2),
            "sonar": round(random.uniform(0.5, 30.0), 2),
        }
        
        # Serialize JSON payload to binary bytes
        payload_bytes = json.dumps(reading).encode('utf-8')
        frame = uamp.create_packet(uamp.TYPE_TELEMETRY, seq, payload_bytes)
        
        sock.sendto(frame, (GATEWAY_HOST, GATEWAY_PORT))
        print(f"[TELEMETRY] seq={seq:04d} sent -> {reading}")
        
        seq += 1
        time.sleep(TELEMETRY_INTERVAL)
        
    sock.close()


# ---------------------------------------------------------------------------
# Command Loop — Reliable Channel (ACK + Retransmission)
# ---------------------------------------------------------------------------
def command_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 100000  # Offset sequence space for commands
    cmd_index = 0

    while _running:
        cmd_name = COMMANDS[cmd_index % len(COMMANDS)]
        cmd_index += 1
        
        payload_data = {"cmd": cmd_name, "issued_at": time.time()}
        payload_bytes = json.dumps(payload_data).encode('utf-8')
        frame = uamp.create_packet(uamp.TYPE_COMMAND, seq, payload_bytes)

        acked = False
        for attempt in range(1, MAX_RETRIES + 1):
            # Simulate link loss by skipping transmission
            if random.random() < PACKET_LOSS_RATE:
                print(f"[COMMAND  ] seq={seq} '{cmd_name}' attempt {attempt} "
                      f"LOST IN TRANSIT (Simulated Loss)")
            else:
                sock.sendto(frame, (GATEWAY_HOST, GATEWAY_PORT))
                print(f"[COMMAND  ] seq={seq} '{cmd_name}' attempt {attempt} sent")

            sock.settimeout(ACK_TIMEOUT)
            try:
                data, _addr = sock.recvfrom(2048)
                msg_type, rec_seq, ack_payload, is_valid = uamp.parse_packet(data)
                
                # Check for valid ACK matching our command sequence
                if is_valid and msg_type == uamp.TYPE_ACK and rec_seq == seq:
                    print(f"[ACK      ] seq={seq} confirmed by gateway "
                          f"(after {attempt} attempt(s))")
                    acked = True
                    break
                else:
                    print(f"[COMMAND  ] seq={seq} unexpected or corrupted response, ignoring")
                    
            except socket.timeout:
                if attempt < MAX_RETRIES:
                    print(f"[COMMAND  ] seq={seq} '{cmd_name}' ACK timeout "
                          f"({ACK_TIMEOUT}s) - Retransmitting...")
                else:
                    print(f"[COMMAND  ] seq={seq} '{cmd_name}' ACK timeout - Giving up")

        if not acked:
            print(f"[COMMAND  ] seq={seq} '{cmd_name}' FAILED after {MAX_RETRIES} attempts")

        seq += 1
        time.sleep(COMMAND_INTERVAL)

    sock.close()


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main():
    print(f"AUV Sender starting -> target gateway {GATEWAY_HOST}:{GATEWAY_PORT}")
    print(f"  telemetry interval : {TELEMETRY_INTERVAL}s")
    print(f"  command interval   : {COMMAND_INTERVAL}s")
    print(f"  simulated loss rate: {PACKET_LOSS_RATE * 100:.0f}%")
    print("-" * 60)

    t1 = threading.Thread(target=telemetry_loop, daemon=True)
    t2 = threading.Thread(target=command_loop, daemon=True)
    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        global _running
        _running = False
        print("\nAUV Sender shutting down...")


if __name__ == "__main__":
    main()