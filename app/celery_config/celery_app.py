from celery import Celery
from app import settings
app = Celery(
    'tasks', broker=f'pyamqp://{settings.RABBITMQ_CRED}@{settings.RABBITMQ_HOST}:5672//')
app.conf.update(
    # task_default_queue='PUBLISH',
    task_acks_late=False,
    # worker_prefetch_multiplier=1,
    # task_publish_retry=True,
    # task_publish_retry_policy={
    #     'max_retries': 3,
    #     'interval_start': 0,
    #     'interval_step': 0.2,
    #     'interval_max': 0.2,
    # },
)
