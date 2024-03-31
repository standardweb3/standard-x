from standard.types.trade import Trade
from standard.types.orderbook import Orderbook
from standard.addresses.matching_engine import matching_engine_addresses
from standard.abis.matching_engine import matching_engine_abi
from web3 import Web3
from eth_account import Account
import aiohttp
import asyncio
import json


class StandardClient:
    def __init__(
        self, private_key: str, http_rpc_url: str, network_name: str, api_key: str
    ) -> None:
        self.provider = Web3.HTTPProvider(http_rpc_url)
        self.w3 = Web3(self.provider)

        # Derive the Ethereum address from the private key
        self.wallet_address = Account.from_key(private_key).address

        # Unlock account with private key
        self.w3.eth.default_account = self.w3.eth.account.from_key(private_key)

        self.matching_engine_address = matching_engine_addresses[network_name]

        self.initialized = True

        # check api-key validity asynchronously check api-key validity
        asyncio.run(self.check_api_key_validity(api_key))
        

        # Optionally, you may want to set other properties or perform additional setup here

    async def check_api_key_validity(self, api_key):
        url = f'https://app.standardweb3.com/api/keys/checkKey?key={api_key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    print("API key is valid.")
                    self.api_key = api_key
                else:
                    print("API key is not valid.")
                    # raise error
                    raise Exception("API key is not valid")

    async def _handle_events(self, tx_hash, contract_abi):
        # get tx receipt
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        if tx_receipt is not None:
            # Parse event logs from the receipt
            for log in tx_receipt["logs"]:
                decoded_log = self.w3.eth.abi.decode_log(
                    contract_abi, log["data"], topics=log["topics"]
                )
                # handle OrderMatched
                if decoded_log.event == "OrderMatched":
                    pass

                # handle OrderPlaced
                if decoded_log.event == "OrderPlaced":
                    pass

            # report result to backend
          
        else:
            print("Transaction receipt not found.")

    async def _send_data_to_backend(url, data, api_key):
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "standardweb3": api_key
                }
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        print("Data sent successfully")
                    else:
                        print(f"Error: {response.status} - {response.reason}")
        except aiohttp.ClientError as e:
            print(f"An error occurred: {e}")

    async def market_buy(self, base, quote, quote_amount, is_maker, n, uid, recipient) -> str:
        # check if the client is initialized
        if self.initialized != True:
            # raise ClientNotInitialized error and return
            raise Exception("Client is not initialized")

        # get abi and address
        contract_address = self.matching_engine_address
        contract_abi = matching_engine_abi

        # make contract object
        contract = self.w3.eth.contract(address=contract_address, abi=contract_abi)

        # make transaction
        try:
            # Estimate gas
            gas_estimate = contract.functions.marketSell(
                base, quote, quote_amount, is_maker, n, uid, recipient
            ).estimateGas(
                {
                    "from": self.address,
                    "nonce": self.w3.eth.getTransactionCount(self.address),
                }
            )

            # Get current gas price from the Ethereum mainnet
            current_gas_price = self.w3.eth.gas_price

            # Build transaction with estimated gas and current gas price
            transaction = contract.functions.marketSell(
                base, quote, quote_amount, is_maker, n, uid, recipient
            ).buildTransaction(
                {
                    "from": self.address,
                    "nonce": self.w3.eth.getTransactionCount(self.address),
                    "gas": gas_estimate * 2,  # Add some buffer for gas estimation
                    "gasPrice": current_gas_price,
                }
            )

            # Sign and send the transaction
            signed_txn = self.w3.eth.account.signTransaction(
                transaction, private_key=self.private_key
            )
            tx_hash = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)

            await self._handle_events(tx_hash, contract_abi)

            return tx_hash.hex()

        except Exception as e:
            print(f"Error: {e}")
            return None

    async def market_sell(self, base, quote, base_amount, is_maker, n, uid, recipient) -> str:
        pass

    async def limit_buy(
        self, base, quote, price, quote_amount, is_maker, n, uid, recipient
    ) -> str:
        pass

    async def limit_sell(
        self, base, quote, price, base_amount, is_maker, n, uid, recipient
    ) -> str:
        pass

    async def show_orderbook(self, base, quote) -> Orderbook:
        pass

    async def recent_trades(self, base, quote) -> list[Trade]:
        self._send_data_to_backend("https://app.standardweb3.com/api/trade/recenttrades", {
            base,
            quote
        }, self.api_key)

    

