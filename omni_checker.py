#!/usr/bin/env python3

import sys
import requests
import time

from requests.exceptions import JSONDecodeError
from typing import Optional


def get_allocation(address: str) -> Optional[float]:
    base_url = "https://omni-issuer-node.clique.tech/credentials"
    data = {
        "pipelineVCName": "omniEcosystemScore", 
        "identifier": "",
        "params": {"walletAddresses": [address]},
    }
    
    try:
        r = requests.post(base_url, json=data)
        query_id = r.json()["queryId"]
        time.sleep(1)  # buggy server cache? dunno
        r = requests.get(f"{base_url}/{query_id}")
        allocation = float(r.json()["data"]["pipelines"]["tokenQualified"])
    except (TypeError, KeyError, JSONDecodeError):
        return None

    return allocation


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: ./omni_checker.py 0xaddress [0xaddress ...]")
        return

    def colorize(txt: str, color: int) -> str:
        return f"\033[{color}m{txt}\033[0m"

    for address in sys.argv[1:]:
        allocation: Optional[float] = get_allocation(address)

        if allocation is None:
            msg = colorize("unexpected reponse (invalid address? region block?)", 33)
        elif allocation > 0:
            msg = colorize(f"{allocation} OMNI", 32)
        else:
            msg = colorize("not eligible", 31)

        print(f"{address}: {msg}")


if __name__ == "__main__":
    main()
