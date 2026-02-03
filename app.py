import os
import traceback
from dotenv import load_dotenv
from timebox_api import TimeboxEvo
from time import sleep

load_dotenv()

TIMEBOX_MAC_ADDR = os.getenv("TIMEBOX_MAC_ADDR")

assert TIMEBOX_MAC_ADDR is not None, print("Is the .env correctly setup?")

berry_face = TimeboxEvo(TIMEBOX_MAC_ADDR)
berry_face.connect()

berry_face.draw_pic("./berry.png")

# berry_face.disconnect()

# Command [45 00 ff ff] shows a dark analog clock for some reason???