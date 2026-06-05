import json
import os
from jsonschema import validate, ValidationError

BASE_DIR = os.path.dirname(__file__)
SCHEMA_PATH = os.path.join(BASE_DIR, "signal_schema.json")

with open(SCHEMA_PATH) as f:
    SCHEMA = json.load(f)


def validate_signal(signal):
    try:
        validate(instance=signal, schema=SCHEMA)
        return True

    except ValidationError as e:
        print("❌ VALIDATION ERROR:", e.message, flush=True)
        raise Exception("Signal validation failed")