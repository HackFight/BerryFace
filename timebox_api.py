import socket
import time

# A message must be in this format: [MESSAGE_PREFIX, PAYLOAD_SIZE_LSB, PAYLOAD_SIZE_MSB, CMD, ARGS, ..., CHECKSUM_LSB, CHECKSUM_MSB, MESSAGE_SUFFIX]
# The prefix and suffix being 0x01 and 0x02 respectively.
# With 0x01, 0x02, and 0x03 being reserved. If they need to be used, masking must be done.
#
# Masking is done by changing the reserved byte to the pair [0x03, byte + 3]
# e.g. 0x01 in the payload must be replaced by [0x03, 0x04]
#
# The checksum is the addition of all the bytes of the payload
#
# Modes:
# 0x00 = Clock
# 0x01 = Temp
# 0x02 = Anim
# 0x03 = Graph
# 0x04 = Image
# 0x05 = Stopwatch
# 0x06 = Scoreboard

MESSAGE_PREFIX = 0x01
MESSAGE_SUFFIX = 0x02

class TimeboxEvo():

    def __init__(self, client_mac_addr):
        self.client_mac_addr = client_mac_addr
        self.bt_socket = None
        self.verbose = True

    def connect(self):
        self.bt_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.bt_socket.settimeout(10)  # Set timeout for connection
        
        if self.verbose:
            print(f"[Server]: Trying to connect to Timebox[{self.client_mac_addr}]")

        self.bt_socket.connect((self.client_mac_addr, 1))
        
        if self.verbose:
            print("[Server]: Connected to Timebox")
        
        time.sleep(0.5)

    def disconnect(self):
        if self.bt_socket:
            self.bt_socket.close()
            if self.verbose:
                print("[Server]: Disconnected from Timebox")
    
    def is_connected(self):
        try:
            data = self.bt_socket.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
            if len(data) == 0:
                return False
            return True

        except BlockingIOError:
            return True

        except (ConnectionResetError, BrokenPipeError, OSError):
            return False

    def send_raw(self, data):
        if self.verbose:
            print_data(data, "SEND")

        self.bt_socket.send(bytes(data))
    
    def recv_response(self, timeout=2.0):
        old_timeout = self.bt_socket.gettimeout()
        self.bt_socket.settimeout(timeout)
        
        try:
            response = self.bt_socket.recv(256)
            if self.verbose:
                print_data(response, "RECV")
            return response

        except socket.timeout:
            if self.verbose:
                print("[Server]: No response received (timeout)")
            return None

        finally:
            self.bt_socket.settimeout(old_timeout)
            
    def send(self, cmd, args, expect_response=True):
        encoded = encode_payload([cmd] + args)
        self.send_raw(encoded)
        
        if expect_response:
            return self.recv_response()
        return None

    def set_rgb(self, r, g, b):
        return self.send(0x6f, [r & 0xff, g & 0xff, b & 0xff])
    
    def set_brightness(self, level):
        return self.send(0x74, [level & 0xff])
    
    def set_mode(self, mode):
        return self.send(0x45, [mode & 0xff])

def mask(data):
    result = []
    for byte in data:
        if byte > 0x03 or byte == 0x00:
            result.append(byte)
        else:
            result += [0x03, byte + 3]
    return result

def unmask(data):
    result = []
    for i in range(len(data)):
        if data[i] == 0x03:
            result.append(data[i+1]-3)
            i+=1
        else:
            result.append(data[i])
    return result


def checksum(data):
    cs = 0
    for byte in data:
        cs += byte
    return cs

def encode_payload(payload):
    final_payload_size = len(payload) + 2

    final_payload_header = [final_payload_size & 0xff, (final_payload_size >> 8) & 0xff]
    cs = checksum(final_payload_header + payload)
    final_payload_suffix = [cs & 0xff, (cs >> 8) & 0xff]

    return [MESSAGE_PREFIX] + mask(final_payload_header + payload + final_payload_suffix) + [MESSAGE_SUFFIX]

def print_data(message, label="DATA"):
    if isinstance(message, bytes):
        message = list(message)
    hex_str = " ".join([f"{i:02x}" for i in message])
    print(f"[{label}]: {hex_str} ({len(message)} bytes)")