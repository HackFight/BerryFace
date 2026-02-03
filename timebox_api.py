import socket
from math import log10, ceil
from time import sleep
from PIL import Image

# A message must be in this format: [MESSAGE_PREFIX, PAYLOAD_SIZE_LSB, PAYLOAD_SIZE_MSB, CMD, ARGS, ..., CHECKSUM_LSB, CHECKSUM_MSB, MESSAGE_SUFFIX]
# The prefix and suffix being 0x01 and 0x02 respectively.
# With 0x01, 0x02, and 0x03 being reserved. If they need to be used, masking must be done (except when sending image data for some reason?).
#
# Masking is done by changing the reserved byte to the pair [0x03, byte + 3]
# e.g. 0x01 in the PAYLOAD must be replaced by [0x03, 0x04], the checksum should NOT be masked!!!
#
# The checksum is the addition of all the bytes of the payload
#
# It is important to wait for a tiny amount of time before sending commands after connection

MESSAGE_PREFIX = 0x01
MESSAGE_SUFFIX = 0x02

class TimeboxEvo():

    def __init__(self, client_mac_addr):
        self.client_mac_addr = client_mac_addr
        self.bt_socket = None
        self.verbose = True

    def connect(self):
        self.bt_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.bt_socket.connect((self.client_mac_addr, 1))
        sleep(0.5)

    def disconnect(self):
        if self.bt_socket:
            sleep(0.5)
            self.bt_socket.close()
    
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
    
    def recv_response(self, timeout=2):
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
            
    def send(self, cmd, args, expect_response=True, masked=True):
        encoded = encode_payload([cmd] + args, masked)
        self.send_raw(encoded)
        
        if expect_response:
            return self.recv_response()
        return None

    def set_rgb(self, r, g, b):
        return self.send(0x6f, [r & 0xff, g & 0xff, b & 0xff], False)
    
    def set_brightness(self, level):
        return self.send(0x74, [level & 0xff], False)
    
    def draw_pic(self, filepath):
        nb_colors, palette, pixel_data = encode_image(filepath)
        frame_size = 7 + len(pixel_data) + len(palette)
        frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, 0, 0, 0, nb_colors]
        frame = frame_header + palette + pixel_data
        prefix = [0x0, 0x0A,0x0A,0x04]
        self.send(0x44, prefix+frame, False, False)
    
    def draw_anim(self, filepaths, speed=100):
        timecode=0
        
        # encode frames
        frames = []
        n=0
        for filepath in filepaths:
            nb_colors, palette, pixel_data = encode_image(filepath)
            frame_size = 7 + len(pixel_data) + len(palette)
            frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, timecode&0xff, (timecode>>8)&0xff, 0, nb_colors]
            frame = frame_header + palette + pixel_data
            frames += frame
            timecode += speed
            n += 1
        
        # send animation
        nchunks = ceil(len(frames)/200.)
        total_size = len(frames)
        for i in range(nchunks):
            chunk = [total_size&0xff, (total_size>>8)&0xff, i]
            self.send(0x49, chunk+frames[i*200:(i+1)*200], False, False)
    
    def draw_gif(self, filepath, speed=100):
        # encode frames
        frames = []
        timecode = 0
        anim_gif = Image.open(filepath)
        for n in range(anim_gif.n_frames):
            anim_gif.seek(n)
            nb_colors, palette, pixel_data = encode_raw_image(anim_gif.convert(mode='RGB'))
            frame_size = 7 + len(pixel_data) + len(palette)
            frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, timecode&0xff, (timecode>>8)&0xff, 0, nb_colors]
            frame = frame_header + palette + pixel_data
            frames += frame
            timecode += speed
        
        # send animation
        nchunks = ceil(len(frames)/200.)
        total_size = len(frames)
        for i in range(nchunks):
            chunk = [total_size&0xff, (total_size>>8)&0xff, i]
            self.send(0x49, chunk+frames[i*200:(i+1)*200], False, False)

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

def encode_payload(payload, masked):
    final_payload_size = len(payload) + 2

    final_payload_header = [final_payload_size & 0xff, (final_payload_size >> 8) & 0xff]
    cs = checksum(final_payload_header + payload)
    rearanged_checksum = [cs & 0xff, (cs >> 8) & 0xff]

    if masked:
        return [MESSAGE_PREFIX] + mask(final_payload_header + payload) + rearanged_checksum + [MESSAGE_SUFFIX]
    else:
        return [MESSAGE_PREFIX] + final_payload_header + payload + rearanged_checksum + [MESSAGE_SUFFIX]

def print_data(message, label="DATA"):
    if isinstance(message, bytes):
        message = list(message)
    hex_str = " ".join([f"{i:02x}" for i in message])
    print(f"[{label}]: {hex_str} ({len(message)} bytes)")

# Code "borrowed" from @virutalabs
def encode_image(filepath):
    img = Image.open(filepath)
    return encode_raw_image(img)
    
def encode_raw_image(img):
    # ensure image is 16x16
    w,h = img.size
    if w == h:
        # resize if image is too big
        if w > 16:
            img = img.resize((16,16))
    
        # create palette and pixel array
        pixels = []
        palette = []
        for y in range(16):
            for x in range(16):
                pix = img.getpixel((x,y))
                
                if len(pix) == 4:
                    r,g,b,a = pix
                elif len(pix) == 3:
                    r,g,b = pix
                if (r,g,b) not in palette:
                    palette.append((r,g,b))
                    idx = len(palette)-1
                else:
                    idx = palette.index((r,g,b))
                pixels.append(idx)
        
        # encode pixels
        bitwidth = ceil(log10(len(palette))/log10(2))
        nbytes = ceil((256*bitwidth)/8.)
        encoded_pixels = [0]*nbytes
        
        encoded_pixels = []
        encoded_byte = ''
        for i in pixels:
            encoded_byte = bin(i)[2:].rjust(bitwidth, '0') + encoded_byte
            if len(encoded_byte) >= 8:
                encoded_pixels.append(encoded_byte[-8:])
                encoded_byte = encoded_byte[:-8]
        encoded_data = [int(c, 2) for c in encoded_pixels]
        encoded_palette = []
        for r,g,b in palette:
            encoded_palette += [r,g,b]
        return (len(palette), encoded_palette, encoded_data)
    else:
        print('[!] Image must be square.')