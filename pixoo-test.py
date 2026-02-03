import os
from pixoo import Pixoo
from dotenv import load_dotenv

load_dotenv()

TIMEBOX_MAC_ADDR = os.getenv("TIMEBOX_MAC_ADDR")

assert TIMEBOX_MAC_ADDR is not None, print("Is the .env correctly setup?")

berry = Pixoo(TIMEBOX_MAC_ADDR)

berry.connect()

berry.draw_gif("./test.gif")