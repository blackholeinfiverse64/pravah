import time
import json


def stream_signals(generator_function):
    while True:
        signals = generator_function()
        yield f"data: {json.dumps(signals)}\n\n"
        time.sleep(2)