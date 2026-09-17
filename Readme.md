# UAMP Protocol

A lightweight simulation of an underwater acoustic messaging protocol built in Python. The project models a simple network between an autonomous underwater vehicle (AUV) and a surface gateway, with packet framing, checksums, telemetry transmission, command messages, acknowledgments, and simulated packet loss.

## Overview

This project demonstrates how a custom network protocol can be layered over UDP-style communication for a noisy underwater environment. It includes:

- frame creation and parsing
- checksum validation
- telemetry generation from an AUV
- reliable command delivery with ACK handling
- simulated packet loss and retransmission
- OpenSSL-compatible encryption benchmarking using `cryptography`

## Project Structure

- `uamp_protocol.py` - defines the packet format and checksum logic
- `auv_sender.py` - simulates an underwater vehicle sending telemetry and commands
- `surface_gateway.py` - receives packets and sends ACKs back to the AUV
- `evaluate_openssl.py` - compares plain UAMP packet size and delay against AES-GCM encryption
- `requirements.txt` - project dependencies

## Protocol Design

The protocol uses a compact binary header for each message:

- magic number
- message type
- sequence number
- payload length
- checksum

This allows the receiver to validate the integrity of incoming packets and detect corrupted or malformed messages.

## Message Types

- `TYPE_TELEMETRY` - periodic sensor data from the AUV
- `TYPE_COMMAND` - commands to be sent reliably
- `TYPE_ACK` - acknowledgment sent by the gateway
- `TYPE_HEARTBEAT` - keep-alive traffic (included in the protocol design)

## How It Works

### AUV Sender
The AUV sender:

1. creates telemetry packets containing sensor values
2. sends them over UDP to the gateway
3. periodically sends command packets
4. waits for ACK responses
5. retries lost commands up to a maximum number of times

### Surface Gateway
The surface gateway:

1. listens for incoming packets
2. validates the packet header and checksum
3. decodes the payload
4. sends ACK packets for valid command messages
5. logs the received telemetry and commands

### Packet Loss Simulation
The project simulates unreliable underwater communication by dropping some packets randomly. This helps demonstrate how command traffic is retried and acknowledged when communication is imperfect.

## Requirements

The project uses only the Python standard library for the core protocol logic, such as:

- `socket`
- `threading`
- `time`
- `json`
- `random`
- `struct`

The only external dependency is `cryptography`, which is used only for the encryption benchmark script:

```bash
pip install -r requirements.txt
```

If you are only running the protocol simulation itself, the built-in Python modules are enough. `cryptography` is needed only when you run `evaluate_openssl.py`.

## Running the Project

Start the gateway first:

```bash
python surface_gateway.py
```

Then start the sender in another terminal:

```bash
python auv_sender.py
```

To benchmark encrypted packet overhead:

```bash
python evaluate_openssl.py
```

## Notes

- This is a simulation and not production-grade underwater networking.
- The protocol is intentionally simple to make the concept easy to understand.
- Packet loss and retransmissions are simulated to model real-world acoustic communication conditions.

## What is `cryptography`?

`cryptography` is a Python library used for secure encryption, decryption, hashing, and key management. It implements modern cryptographic algorithms such as AES, RSA, and hashing functions.

In this project, it is used to demonstrate how standard encryption (AES-GCM) affects packet size and processing time compared to plain UAMP payloads. In other words, it helps show the cost of adding confidentiality to transmitted data.

Typical uses of `cryptography` include:

- encrypting files or network payloads
- securing API traffic
- generating and managing keys
- implementing TLS / secure communication
- benchmarking performance of encryption operations

## License

This project is provided for learning and experimentation.
