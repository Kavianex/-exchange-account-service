from kafka.consumer import consume as kafka_concumer
from internal import enums, match
from datetime import datetime as dt
import json
import time


def event_handler(event):
    t1 = time.time()
    utc_now = dt.utcnow()
    event = json.loads(event)
    if event['topic'] == enums.EeventTopic.order_update.value:
        match.receive_order(event['event'])
    t2 = time.time()
    print(f"recv: {utc_now} done in {t2 - t1}s")


if __name__ == "__main__":
    kafka_concumer(event_handler)
