from kafka.consumer import consume as kafka_concumer
from internal import enums, match
import json


def event_handler(event):
    event = json.loads(event)
    if event['topic'] == enums.EeventTopic.order_update.value:
        match.receive_order(event)


if __name__ == "__main__":
    kafka_concumer(event_handler)
