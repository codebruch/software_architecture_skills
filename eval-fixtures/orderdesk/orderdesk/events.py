import json
import threading
import time

from orderdesk import config

_queue = []


def publish(event_type, payload):
    _queue.append({"type": event_type, "payload": payload, "at": time.time()})


def _drain_forever():
    while True:
        while _queue:
            event = _queue.pop(0)
            try:
                with open(config.EVENTS_LOG, "a") as f:
                    f.write(json.dumps(event) + "\n")
            except Exception:
                pass
        time.sleep(0.5)


_worker = threading.Thread(target=_drain_forever, daemon=True)
_worker.start()
