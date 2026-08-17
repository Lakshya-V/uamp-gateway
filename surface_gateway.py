import socket
import json
import uamp_protocol as uamp

# GATEWAY CONFIGURATION
HOST = "127.0.0.1"  # Localhost for testing (use "0.0.0.0" for real network)
PORT = 5000         # UDP listening port

def start_gateway():
    # 1. Create a UDP Socket (AF_INET = IPv4, SOCK_DGRAM = UDP)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((HOST, PORT))
    
    print(f"==================================================")
    print(f"[UAMP GATEWAY] Surface Station Active on {HOST}:{PORT}")
    print(f"==================================================\n")

    try:
        while True:
            # 2. Receive raw bytes from network (buffer size 2048 bytes)
            raw_bytes, sender_address = server_socket.recvfrom(2048)
            
            # 3. Parse packet using custom protocol library
            msg_type, seq_num, payload, is_valid = uamp.parse_packet(raw_bytes)
            
            # --- VALIDATION CHECKS ---
            if msg_type is None:
                print(f"[REJECTED] Invalid Magic Number or malformed header from {sender_address}")
                continue
                
            if not is_valid:
                print(f"[CORRUPTED] Packet #{seq_num} failed checksum check! Dropping.")
                continue

            # --- PROCESS VALID PACKETS ---
            # Parse JSON payload string back into Python dictionary
            try:
                data = json.loads(payload.decode('utf-8'))
            except json.JSONDecodeError:
                data = payload.decode('utf-8')

            # --- ROUTING LOGIC BASED ON PROTOCOL FLAG ---
            if msg_type == uamp.TYPE_TELEMETRY:
                print(f"[TELEMETRY | UDP] Seq #{seq_num} from {sender_address}")
                print(f" └── Data: {data}")
                
            elif msg_type == uamp.TYPE_COMMAND:
                print(f"[COMMAND | RELIABLE] Seq #{seq_num} from {sender_address}")
                print(f" └── Executing: {data}")
                
                # --- AUTOMATIC ACKNOWLEDGMENT RESPONSE ---
                # Build an ACK packet back to sender to prevent retransmission
                ack_payload = json.dumps({"status": "SUCCESS", "ack_seq": seq_num}).encode('utf-8')
                ack_packet = uamp.create_packet(uamp.TYPE_ACK, seq_num, ack_payload)
                
                server_socket.sendto(ack_packet, sender_address)
                print(f" └── [SENT ACK] Packet #{seq_num} confirmed back to AUV.")

            elif msg_type == uamp.TYPE_HEARTBEAT:
                print(f"[HEARTBEAT] AUV Connection Alive (Seq #{seq_num})")

            print("-" * 50)

    except KeyboardInterrupt:
        print("\n[UAMP GATEWAY] Shutting down surface gateway...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_gateway()