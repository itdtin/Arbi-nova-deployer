import json
import os
from pathlib import Path
from typing import Union, Dict

import solcx
from loguru import logger

import app.config as config

logger.add(
        "log/utils.log",
        format="{time} | {level} | {message}",
        level="DEBUG",
    )


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        else:
            cls._instances[cls].__init__(*args, **kwargs)
        return cls._instances[cls]


def get_solc_version():
    for v in solcx.get_installable_solc_versions():
        if str(v) == config.SOL_COMPILER_V:
            return v
        solcx.install_solc(config.SOL_COMPILER_V)


def get_file_content(path_from_root: Path):
    with open(path_from_root.absolute().as_posix(), "r", encoding='utf8') as file:
        raw_contract = file.read()
        return raw_contract, path_from_root.name


def save_to_file(path: Path, data: Union[str, Dict]):
    path_str = path.absolute().as_posix()
    try:
        folder_path = path_str[:path_str.index(path.name)]
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        data = data if isinstance(data, str) else json.dumps(data)
        with open(path_str, 'w+') as file:
            file.write(data)
    except Exception as e:
        logger.error(f"Can't save file: {path_str}")
