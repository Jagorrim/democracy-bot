from dotenv import find_dotenv, load_dotenv
import os

load_dotenv(find_dotenv())

token = os.getenv('token')
approval_emoji = os.getenv('approval_emoji')
