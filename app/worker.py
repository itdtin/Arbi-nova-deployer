import random
from pathlib import Path
from time import sleep
from typing import Dict, List
import json

import solcx
from eth_account.signers.local import LocalAccount
from solcx import compile_source, install_solc
from loguru import logger
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
from web3.types import ABI
from web3.exceptions import TransactionNotFound

import app.config as config
from app.utils import save_to_file, get_solc_version, get_file_content


logger.add(
        "log/deployer.log",
        format="{time} | {level} | {message}",
        level="INFO",
    )


class Deployer:
    default_gas_limit = 1_000_000

    def __init__(self, *args, **kwargs):
        """Initializes the `web3` object.

        Args:
            rpc_provider (HTTPProvider): Valid `web3` HTTPProvider instance (optional)
        """
        rpc_provider = kwargs.pop('RPC_URL', None)
        if not rpc_provider:
            timeout = getattr(config, "NODE_TIMEOUT", 10)

            uri = config.NETWORK_URL
            rpc_provider = HTTPProvider(
                endpoint_uri=uri,
                request_kwargs={
                    "timeout": timeout
                }
            )

        self.web3 = Web3(rpc_provider)

        # If running in a network with PoA consensus, inject the middleware
        if getattr(config, "GETH_POA", False):
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    def deploy_contract(self, bytecode: str, abi_path: str, wallet: LocalAccount, gas_limit: int = default_gas_limit) -> (str, ABI):
        """Деплой контракта."""

        contract = self.web3.eth.contract(
            bytecode=bytecode,
            abi=json.load(Path(abi_path).open())
        )

        transaction = contract.constructor().buildTransaction(
            {
                "chainId": self.web3.eth.chain_id,
                "gasPrice": self.web3.eth.gas_price,
                "gas": gas_limit,
                "from": wallet.address,
                "value": 0,
                "nonce": self.web3.eth.getTransactionCount(wallet.address)
            }
        )

        signed_txn = wallet.sign_transaction(transaction)
        try:
            txn_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            contract_address = self.web3.eth.wait_for_transaction_receipt(
                txn_hash).contractAddress
            logger.info(
                f"Deploy contract by {wallet.address}, transaction: {txn_hash.hex()}.")
            sleep(random.randint(20, 40))
            return contract_address, contract.abi
        except TransactionNotFound as e:
            logger.error("Can't send transaction to deploy contract")
            raise e

    def send_and_return_ether(self, wallet: LocalAccount, to: str, abi,
                              amount_min: float = config.AMOUNT_LOW, amount_max: float = config.AMOUNT_HIGH):
        self.send_eth_to_contract(
            wallet=wallet,
            to_address=to,
            amount=random.uniform(amount_min, amount_max),
        )

        sleep(random.randint(7, 15))

        self.return_eth_from_contract(wallet, to, abi)

    def send_eth_to_contract(self, wallet: LocalAccount, to_address: str, amount: float) -> None:
        """Отправка указанного количества эфиров на контракт."""

        dict_transaction = {
            "chainId": self.web3.eth.chain_id,
            "from": wallet.address,
            "to": self.web3.toChecksumAddress(to_address),
            "value": self.web3.toWei(amount, "ether"),
            "gas": 300_000,
            "gasPrice": self.web3.eth.gas_price,
            "nonce": self.web3.eth.getTransactionCount(wallet.address),
        }

        signed_txn = wallet.sign_transaction(dict_transaction)
        txn_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        logger.info(
            f"Send {amount} eth to {to_address}, transaction: {txn_hash.hex()}")

    def return_eth_from_contract(self, wallet: LocalAccount, contract_address: str, abi: ABI
                                 ) -> None:
        """Возврат всего баланса из контракта на кошелёк-создатель."""

        dict_transaction = {
            "chainId": self.web3.eth.chain_id,
            "from": wallet.address,
            "value": 0,
            "gas": 500_000,
            "gasPrice": self.web3.eth.gas_price,
            "nonce": self.web3.eth.getTransactionCount(wallet.address),
        }

        contract = self.web3.eth.contract(
            address=self.web3.toChecksumAddress(contract_address), abi=abi)

        transaction = contract.functions.MoneyBack().buildTransaction(dict_transaction)
        signed_txn = wallet.sign_transaction(transaction)

        txn_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        logger.info(
            f"Return balance from contract, transaction: {txn_hash.hex()}.")

    @staticmethod
    def save_new_contract_data(data: Dict, folder_name: str):
        path = Path(f"{config.CREATE_CONTRACTS_PATH}/{folder_name}/data.json")
        save_to_file(path, data)

    @staticmethod
    def compile_contract(contract_code: str):
        install_solc(get_solc_version())
        return compile_source(contract_code, optimize=True, optimize_runs=3, output_values=['abi', 'bin'])

    @staticmethod
    def compile_contract_file(path: str):
        solc_v = get_solc_version()
        try:
            solcx.install_solc(solc_v)
            solcx.set_solc_version(solc_v)
            compilation = solcx.compile_files(
                [path],
                output_values=["abi", "bin-runtime"],
                solc_version=solc_v,
                optimize=True,
                optimize_runs=200
            )
            contract_bytecode = compilation[list(compilation.keys())[0]]['bin-runtime']
            print(contract_bytecode[:100], solc_v, "compiled")
            return contract_bytecode
        except Exception:
            pass

    @staticmethod
    def compile_contract_file_v2(file_path: Path):
        solc_v = get_solc_version()
        file = file_path.name
        spec = {
            "language": "Solidity",
            "sources": {
                file: {
                    "urls": [
                        file_path.absolute().as_posix()
                    ]
                }
            },
            "settings": {
                "optimizer": {
                    "enabled": True
                },
                "outputSelection": {
                    "*": {
                        "*": [
                            "metadata", "evm.bytecode", "abi"
                        ]
                    }
                }
            }
        }
        out = solcx.compile_standard(spec, allow_paths=["."], solc_version=solc_v)
        bytecode = out["contracts"][file][file.split(".")[0]]["evm"]["bytecode"]["object"]
        abi = out["contracts"][file][file.split(".")[0]]["abi"]
        return bytecode, abi

    def create_uniq_contracts(
            self,
            file_path: Path,
            count_of_new: int = 1,
            search_symbol: str = "\n",
            max_to_add: int = 4
    ):
        contract_code, contract_name = get_file_content(file_path)
        indexes = [index for index, char in enumerate(contract_code) if char == search_symbol]
        start = 0
        while start < count_of_new:
            new_contract_code = self.modify_contract_code(contract_code, indexes, "\n", max_to_add)
            path = Path(f"{config.CREATE_CONTRACTS_PATH}/{str(start)}/{contract_name}")
            save_to_file(path, new_contract_code)
            logger.info(f"New contract created on path: {path.absolute().as_posix()}")
            start += 1

    @staticmethod
    def modify_contract_code(contract_code: str, insert_indexes: List[int], insert_symbol: str, insert_max_amount: int):
        """
        @param contract_code initial contract code
        @param insert_indexes the list of indexes of search symbol in initial code
        @param insert_symbol symbol to insert
        @param insert_max_amount how much max characters to add
        """
        new_code = contract_code
        offset = 0
        indexes_to_change = random.sample(insert_indexes, random.randint(0, len(insert_indexes)))
        indexes_to_change.sort()
        start_code_index = new_code.index("{")
        for index in indexes_to_change:
            index += offset
            amount_of_extra_breaks = random.randint(0, insert_max_amount)
            if index > start_code_index:
                new_code = new_code[:index] + insert_symbol * amount_of_extra_breaks + new_code[index:]
                offset += amount_of_extra_breaks
        return new_code
