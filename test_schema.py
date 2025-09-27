import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent / "src"))

from underwriter.schema import Assumptions

# Path to your JSON file
path = Path(__file__).parent / "scenarios" / "sample_assumptions.json"

# Load the JSON data
with open(path, "r") as f:
    data = json.load(f)

# Validate with Pydantic
try:
    assumptions = Assumptions(**data)
    print("✅ Validation passed!")
    print(assumptions)
except Exception as e:
    print("❌ Validation failed:")
    print(e)
