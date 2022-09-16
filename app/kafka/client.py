from kafka.producer import KafkaProducer
from internal import enums
from pydantic import BaseModel
import time
import json


def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
    if err is not None:
        print('Message delivery failed: {}'.format(err))
        success = False
    else:
        print('Message delivered to {} [{}]'.format(
            msg.topic(), msg.partition()))
        success = True
    return success


def publish(info: BaseModel, event_type: enums.EventType, symbol: str = ""):
    events = []
    info_json = info.serialize()
    if event_type == enums.EventType.send_order.value:
        events.append({
            "info": info_json,
            "queue": enums.KafkaQueue.match_engine.value,
            "topic": enums.EeventTopic.order_update.value,
            "key": info.symbol,
        })
        events.append({
            "info": info_json,
            "queue": enums.KafkaQueue.account.value,
            "topic": enums.EeventTopic.order_update.value,
            "key": str(info.account_id),
        })
    elif event_type == enums.EventType.cancel_order.value:
        events.append({
            "info": info_json,
            "queue": enums.KafkaQueue.match_engine.value,
            "topic": enums.EeventTopic.order_update.value,
            "key": info.symbol,
        })
    elif event_type == enums.EventType.update_order.value:
        events.append({
            "info": info_json,
            "queue": enums.KafkaQueue.account.value,
            "topic": enums.EeventTopic.order_update.value,
            "key": str(info.account_id),
        })
    elif event_type == enums.EventType.trade.value:
        events.append({
            "info": info_json,
            "queue": enums.KafkaQueue.public.value,
            "topic": enums.EeventTopic.trade.value,
            "key": f"{info.symbol}:{enums.EeventTopic.trade.value}",
        })
    elif event_type == enums.EventType.order_book.value:
        events.append({
            "info": info_json,
            "queue": enums.KafkaQueue.public.value,
            "topic": f"{symbol}:{enums.EeventTopic.order_book.value}",
            "key": f"{symbol}:{enums.EeventTopic.order_book.value}",
        })
    elif event_type == enums.EventType.sub_trade.value:
        events.append({
            "info": info_json,
            "queue": enums.KafkaQueue.account.value,
            "topic": enums.EeventTopic.account_trade.value,
            "key": str(info.account_id),
        })
    elif event_type == enums.EventType.balance.value:
        events.append({
            "info": info_json,
            "queue": enums.KafkaQueue.account.value,
            "topic": enums.EeventTopic.balance.value,
            "key": str(info.account_id),
        })

    for event in events:
        _produce(**event)


def _produce(info: dict, topic: str, key: str = "", queue: str = "", callback=callable):
    event = {
        'topic': topic,
        'timestamp': int(1000 * time.time()),
        'event': info,
    }
    msg = json.dumps(event).encode('utf8')
    KafkaProducer.produce(queue, key=key, value=msg, callback=callback)
