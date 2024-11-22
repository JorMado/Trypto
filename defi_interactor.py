import json
from web3 import Web3
from gasOracle import GasOracle

class DeFiInteractor:
    def __init__(self, web3_provider):
        self.w3 = Web3(Web3.HTTPProvider(web3_provider))
        self.contracts = {}
        self.gas_oracle = GasOracle()
        
    async def execute_swap(self, route, amount, max_slippage):
        gas_price = await self.gas_oracle.get_optimal_gas_price()
        
        transaction = {
            'from': self.address,
            'gasPrice': gas_price,
            'nonce': await self.w3.eth.get_transaction_count(self.address),
            'data': self._encode_swap_data(route, amount)
        }
        
        signed_txn = self.w3.eth.account.sign_transaction(
            transaction, self.private_key
        )
        tx_hash = await self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        return await self.w3.eth.wait_for_transaction_receipt(tx_hash)