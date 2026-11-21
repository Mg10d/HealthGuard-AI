import os
import sys

# Make the project folder importable when running `pytest` from it.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
