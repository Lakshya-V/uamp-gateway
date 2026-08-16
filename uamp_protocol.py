# A shared library containing pack_frame() and unpack_frame() logic using Python's struct module, along with a calculate_checksum() function.
import struct

# PROTOCOL CONSTANTS
# 2-Byte Magic Number to identify valid UAMP frames
MAGIC_NUMBER = 0x1A2B  

# Message Type Flags
TYPE_TELEMETRY = 0x01  # UDP Stream (High frequency, loss-tolerant)
TYPE_COMMAND   = 0x02  # TCP / Reliable Stream (Requires ACK)
TYPE_ACK       = 0x03  # Acknowledgment response
TYPE_HEARTBEAT = 0x04  # Keep-alive check

# Header layout size: 2 + 1 + 4 + 2 + 2 = 11 bytes
HEADER_SIZE = 11

# Format: ! (Big-Endian Network Order)
# H = uint16 (2B), B = uint8 (1B), I = uint32 (4B)
HEADER_FORMAT = "!H B I H H"


# CHECKSUM HELPER

def calculate_checksum(data: bytes) -> int:
    """Calculates a simple 16-bit sum over payload bytes."""
    if not data:
        return 0
    # Sum byte values modulo 65535 (2-byte unsigned max)
    return sum(data) % 65535


# PACKET CREATION (SERIALIZATION)

def create_packet(msg_type: int, seq_num: int, payload: bytes) -> bytes:
    """
    Packs protocol fields and payload into a raw byte stream.
    """
    payload_len = len(payload)
    checksum = calculate_checksum(payload)
    
    # Pack header fields into 11 binary bytes
    header = struct.pack(
        HEADER_FORMAT,
        MAGIC_NUMBER,
        msg_type,
        seq_num,
        payload_len,
        checksum
    )
    
    # Return header glued with binary payload
    return header + payload



# PACKET PARSING (DESERIALIZATION)

def parse_packet(raw_data: bytes):
    """
    Parses a raw byte stream into structured header values and payload.
    Returns: (msg_type, seq_num, payload, is_valid) or (None, None, None, False)
    """
    # 1. Check if we received at least a full header
    if len(raw_data) < HEADER_SIZE:
        return None, None, None, False
    
    # 2. Extract header bytes and unpack
    header_bytes = raw_data[:HEADER_SIZE]
    magic, msg_type, seq_num, payload_len, checksum = struct.unpack(
        HEADER_FORMAT, 
        header_bytes
    )
    
    # 3. Validate Magic Number
    if magic != MAGIC_NUMBER:
        return None, None, None, False
    
    # 4. Extract Payload
    payload = raw_data[HEADER_SIZE : HEADER_SIZE + payload_len]
    
    # 5. Verify Checksum
    computed_checksum = calculate_checksum(payload)
    is_valid = (computed_checksum == checksum)
    
    return msg_type, seq_num, payload, is_valid