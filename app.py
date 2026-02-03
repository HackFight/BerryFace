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

berry_face.set_rgb(255, 0, 0)

berry_face.disconnect()