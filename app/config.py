import os

import dotenv

dotenv.load_dotenv()

NETWORK_URL: str = os.environ.get("NETWORK_URL")
AMOUNT_LOW: float = float(os.environ.get("AMOUNT_LOW"))
AMOUNT_HIGH: float = float(os.environ.get("AMOUNT_HIGH"))
GAS_LIMIT: str = os.environ.get("GAS_LIMIT")

SOL_COMPILER_V: str = "0.8.0"
NODE_TIMEOUT: int = 20

CREATE_CONTRACTS_PATH: str = "new_contracts"
CONTRACT_PATH: str = "contract"
CONTRACT_NAME: str = "CryptoSchool"

"0xc4448b71118c9071Bcb9734A0EAc55D18A153949" # -контракт бриджа arbitrum nova на эфире