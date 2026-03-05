import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    "KEYS": os.path.join(BASE_DIR, "Keys"),
    "LOGS": os.path.join(BASE_DIR, "Logs"),
}

def init_directories():
    for path in DIRS.values():
        os.makedirs(path, exist_ok=True)