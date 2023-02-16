from confluent_kafka import Consumer
from internal import enums
import settings


def consume(callback: callable):
    c = Consumer({
        'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'match-engine',
        # 'auto.create.topics.enable': True,
        'auto.offset.reset': 'earliest',
        'api.version.request.timeout.ms': 300000,
    })
    topics = [enums.KafkaQueue.match_engine.value]
    c.subscribe(topics)
    print(f"consumer subscribed: {topics}")

    while True:
        msg = c.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            continue
        msg = msg.value().decode('utf-8')
        callback(msg)
        # try:
        #     callback(msg)
        # except Exception as e:
        #     print(e)
    c.close()
