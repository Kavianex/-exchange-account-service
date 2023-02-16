import settings
from celery_config.celery_app import app
from orm import database, models
from internal import enums
import json
import requests
import time


class Network:
    def __init__(self, network) -> None:
        self.network = network
        self.address = network.address
        self.confirmations = network.confirmations
        self.last_confirmed_block = network.last_updated_block
        self.base_url = network.rpc_url
        self.apikey = settings.ETHERSCAN_APIKEY
        self.contract_address = self.get_asset_contract_address()

    def get_asset_contract_address(self):
        db = next(database.get_db())
        asset = db.query(models.Asset).filter(
            models.Asset.network == self.network
        ).one()
        return asset.contract_address

    def send_request(self, params):
        params['apikey'] = self.apikey
        response = requests.get(url=self.base_url, params=params)
        return response.json()

    def get_transactions(self):
        block_number = self.get_last_block_number()
        last_valid_block = block_number - self.confirmations
        params = {
            "module": "account",
            "action": "tokentx",
            "contractaddress": self.contract_address,
            "address": self.address,
            "page": 1,
            "offset": 100,
            "startblock": self.last_confirmed_block,
            "endblock": last_valid_block,
            "sort": "desc",
        }
        trxs = self.get_all_results(params=params)
        return trxs

    def get_all_results(self, params):
        pages = self.send_request(params=params)
        return pages['result']

    def get_last_block_number(self):
        params = {
            "module": "proxy",
            "action": "eth_blockNumber",
        }
        block = self.send_request(params=params)
        return int(block['result'], base=16)


class Explorer:

    @classmethod
    def get_networks(cls):
        networks = []
        db = next(database.get_db())
        db_networks = db.query(models.Network).all()
        for _network in db_networks:
            networks.append(Network(network=_network))
        return networks

    @classmethod
    def explore(cls):
        networks = cls.get_networks()
        for network in networks:
            raw_transactions = network.get_transactions()
            cleaned_transactions = cls.clean_transactions(
                raw_transactions, required_confirmations=network.confirmations)
            info = {
                "network_address": network.address,
                "asset_contract_address": network.contract_address,
                "transactions": cleaned_transactions,
            }
            app.send_task("tasks.create_transactions", args=[
                          info], queue=enums.QueueName.blockchain.value)

    @classmethod
    def clean_transactions(cls, transactions, required_confirmations):
        cleaned = []
        for transaction in transactions:
            trx_confirmations = int(transaction['confirmations'])
            if trx_confirmations < required_confirmations:
                continue
            _trx = {
                "block_number": int(transaction['blockNumber']),  # "8478708",
                # "1676198052",
                "timestamp": int(transaction['timeStamp'])*1000,
                # "0x1e0c337d5cb4e0e95713c8e2153de63b5c8cb1e14cf9ae3dd11482b7df38efd2",
                "hash": transaction['hash'],
                # "nonce": int(transaction['nonce']),#"0",
                # "block_hash": transaction['blockHash'],#"0x54ca6bd28bc734d3282ffaae600ee125ce69d435b069b0ad22303b23ff291d50",
                # "0x04783562cea329a593f4c8af534fff025715ad31",
                "from": transaction['from'].lower(),
                # "0xc2c527c0cacf457746bd31b2a698fe89de2b6d49",
                "contract_address": transaction['contractAddress'].lower(),
                # "0x8e7641f3c103bba891c6c2a535e592271ebd8694",
                "to": transaction['to'].lower(),
                "value": int(transaction['value']),  # "19163436",
                # "token_name": transaction['tokenName'],#"USDT",
                # "token_symbol": transaction['tokenSymbol'],#"USDT",
                "token_decimal": int(transaction['tokenDecimal']),  # "6",
                # "transaction_index": int(transaction['transactionIndex']),#"61",
                # "gas": int(transaction['gas']),#"218125",
                # "gas_price": int(transaction['gasPrice']),#"1500000034",
                # "gas_used": int(transaction['gasUsed']),#"143164",
                # "cumulative_gas_used": int(transaction['cumulativeGasUsed']),#"14627011",
                # "input": transaction['input'],#"deprecated",
                "confirmations": trx_confirmations,  # "16329"
            }
            cleaned.append(_trx)
        return cleaned

    @classmethod
    def create_transactions(info):

        pass


# Explorer.explore()
