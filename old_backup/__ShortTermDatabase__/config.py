import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    username = os.getenv("username")
    userpath = os.getenv("userpath")

    @classmethod
    def validate(cls):
        required = [
            "username",
            "userpath",
        ]
        missing = [k for k in required if not getattr(cls, k)]
        if missing:
            raise ValueError(f"Missing required config values: {', '.join(missing)}")


if __name__ == "__main__":

    try:
        Config.validate()
        print("All required configuration values are set.")
    except ValueError as e:
        print(e)

    print(Config.userpath)
