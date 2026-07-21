#!/usr/bin/env python----------------------------------------------------------------------

import subprocess
import sys

print("🚀 Setting up ShortTermDatabase...\n")

# Check Python version
if sys.version_info < (3, 10):
    print(
        f"❌ Python 3.10+ required. You have {sys.version_info.major}.{sys.version_info.minor}"
    )
    sys.exit(1)

# Ask user preference
print("Choose setup:")
print("  1. Poetry (recommended)")
print("  2. pip (simple)")

choice = input("\nChoice (1/2): ").strip()

try:
    if choice == "1":
        subprocess.run(
            "python -m poetry config virtualenvs.in-project true --local",
            shell=True,
            check=True,
        )
        subprocess.run("python -m poetry install", shell=True, check=True)
        print("\n✅ Done! Run: python -m poetry shell")

    elif choice == "2":
        subprocess.run("pip install --user -e .", shell=True, check=True)
        print("\n✅ Done! Imports ready.")

    else:
        print("❌ Invalid choice")
        sys.exit(1)

except subprocess.CalledProcessError:
    print("❌ Setup failed")
    sys.exit(1)
