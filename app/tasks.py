from internal import match
from celery_config.celery_app import app
from celery import shared_task
from blockchain_explorer import Explorer as BlockchainExplorer


@app.task
def match_engine(event):
    match.receive_order(event)


@shared_task
def blockchain_explore():
    BlockchainExplorer.explore()


@shared_task
def create_transactions(transactions_info):
    BlockchainExplorer.create_transactions(transactions_info)
