import sys
from dataclasses import dataclass
from config import Config

Config.validate()

if Config.userpath not in sys.path:
    sys.path.append(Config.userpath)

import powerfactory

app = powerfactory.GetApplication()
# --- Show the PowerFactory application

if __name__ == "__main__":

    if app is None:
        print("Error: Could not connect to PowerFactory application.")
        sys.exit(1)
    else:
        print("Successfully connected to PowerFactory application.")
