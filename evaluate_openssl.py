"""
Measures performance metrics comparing Plain UAMP vs. OpenSSL Encrypted UAMP.
"""

import time
import importlib
import uamp_protocol as uamp

try:
    AESGCM = importlib.import_module(
        "cryptography.hazmat.primitives.ciphers.aead"
    ).AESGCM
except ImportError as exc:
    raise SystemExit(
        "This benchmark requires the 'cryptography' package. "
        "Install it with: python -m pip install cryptography"
    ) from exc

# 1. METRIC: FRAME OVERHEAD & BANDWIDTH
print("==================================================")
print("1. EVALUATING FRAME SIZE & OVERHEAD")
print("==================================================")

# Create a sample telemetry payload
sample_payload = b'{"depth": 42.5, "pitch": -3.2, "roll": 1.1}'
plain_frame = uamp.create_packet(uamp.TYPE_TELEMETRY, 1, sample_payload)

plain_size = len(plain_frame)
print(f"Plain UAMP Packet Size: {plain_size} Bytes (11B Header + {len(sample_payload)}B Payload)")

# AES-256-GCM symmetric key setup (OpenSSL standard)
key = AESGCM.generate_key(bit_length=256)
aesgcm = AESGCM(key)
nonce = b"unique_nonce1"  # 12-byte initialization vector

# Encrypt UAMP payload
encrypted_payload = aesgcm.encrypt(nonce, sample_payload, None)
secure_frame = uamp.create_packet(uamp.TYPE_TELEMETRY, 1, encrypted_payload)

secure_size = len(secure_frame) + len(nonce)  # Frame + Nonce size
overhead = secure_size - plain_size
penalty_pct = (overhead / plain_size) * 100

print(f"Secured UAMP Packet Size: {secure_size} Bytes")
print(f"OpenSSL Encryption Overhead: +{overhead} Bytes (+{penalty_pct:.1f}% bandwidth growth)\n")

# 2. METRIC: PROCESSING LATENCY (BENCHMARK)
print("==================================================")
print("2. EVALUATING PROCESSING TIME (10,000 PACKETS)")
print("==================================================")

ITERATIONS = 10000

# Benchmark Plain Serialization
start_time = time.perf_counter()
for i in range(ITERATIONS):
    pkt = uamp.create_packet(uamp.TYPE_TELEMETRY, i, sample_payload)
plain_duration = time.perf_counter() - start_time

# Benchmark Encrypted Serialization (OpenSSL AES-GCM)
start_time = time.perf_counter()
for i in range(ITERATIONS):
    enc_data = aesgcm.encrypt(nonce, sample_payload, None)
    pkt = uamp.create_packet(uamp.TYPE_TELEMETRY, i, enc_data)
secure_duration = time.perf_counter() - start_time

plain_us = (plain_duration / ITERATIONS) * 1_000_000
secure_us = (secure_duration / ITERATIONS) * 1_000_000

print(f"Plain UAMP Creation Time:   {plain_us:.2f} microseconds / packet")
print(f"Secured UAMP Creation Time: {secure_us:.2f} microseconds / packet")
print(f"Encryption Processing Delay: +{secure_us - plain_us:.2f} microseconds / packet")
print("==================================================")