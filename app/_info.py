from os import getenv
from dotenv import load_dotenv

load_dotenv()

__version__ = "1.3.0"
__author__ = 'Shirogutama'
__token__ = getenv("AUTHENTICATION_KEY", "")
