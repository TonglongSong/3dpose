import time
from my_utils import clean_history
import os

current_path = os.getcwd()
while True:
    clean_history(300, current_path)
    time.sleep(300)