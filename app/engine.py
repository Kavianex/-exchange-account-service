from kafka.consumer import consume as kafka_concumer
from internal import enums, match
import json
import time


def event_handler(event):
    t1 = time.time()
    event = json.loads(event)
    if event['topic'] == enums.EeventTopic.order_update.value:
        match.receive_order(event['event'])
    t2 = time.time()
    print(f"done in {t2 - t1} s")


if __name__ == "__main__":
    kafka_concumer(event_handler)
