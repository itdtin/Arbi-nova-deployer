from pathlib import Path
from typing import List

from eth_account.signers.local import LocalAccount
from loguru import logger
from web3 import Account

from app import config
from app.worker import Deployer

logger.add(
    "log/main.log",
    format="{time} | {level} | {message}",
    level="DEBUG",
)


def load_wallets() -> List[LocalAccount]:
    """Загрузка кошельков из текстовика."""

    file = Path("./wallets.txt").open()
    return [Account.from_key(line.replace("\n", "")) for line in file.readlines()]


def main() -> None:
    logger.info("Start.")
    wallets = load_wallets()
    logger.info("Load wallets.")
    existing_contract_path = Path(f"{config.CONTRACT_PATH}/{config.CONTRACT_NAME}.sol")
    deployer = Deployer()
    deployer.create_uniq_contracts(existing_contract_path, len(wallets))

    for i, wallet in enumerate(wallets):
        new_contract_path = Path(f"{config.CREATE_CONTRACTS_PATH}/{i}/{existing_contract_path.name}")
        bytecode, _ = deployer.compile_contract_file_v2(new_contract_path)
        logger.info("Load bytecode.")

        contract_address, abi = deployer.deploy_contract(
            bytecode,
            f"./{config.CONTRACT_PATH}/{config.CONTRACT_NAME}.abi.json", wallet
        )
        deployer.send_and_return_ether(wallet, contract_address, abi)

        deployer.save_new_contract_data(
            {"bytecode": bytecode, "address": contract_address, "owner": wallet.address}, str(i)
        )
        logger.success(f"{i+1}/{len(wallets)}")

    logger.success("Finish.")
