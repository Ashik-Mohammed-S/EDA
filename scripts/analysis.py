from pathlib import Path
from scripts.exploratory import build

def run(mode="full"):
    # Both modes retain the full descriptive population; no EDA sampling.
    return build(Path(__file__).resolve().parents[1],"bank")
