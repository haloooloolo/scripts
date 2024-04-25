#!/usr/bin/env python3

import ssl
import json
from urllib.request import urlopen

from typing import Optional, Union


def read_hex_addr(addr_type: str, target_len: int) -> str:
    def is_valid(_addr: str) -> bool:
        try:
            int(_addr, 16)
            prefix = '0x'
            return _addr.startswith(prefix) and ((len(_addr) - len(prefix)) == target_len)
        except ValueError:
            return False

    def read() -> str:
        return input(f'{addr_type} address: ').strip()

    while not is_valid(addr := read()):
        print(f'not a valid {addr_type} address, try again')

    return addr


def main():
    eth_address = read_hex_addr('ETH', 40)
    starknet_address = read_hex_addr('StarkNet', 64)

    def get_merkle_info() -> Optional[dict[str, Union[str, list, int]]]:
        context = ssl._create_unverified_context()
        for i in range(10):
            url = f'https://raw.githubusercontent.com/starknet-io/provisions-data/main/eth/eth-{i}.json'
            print(f'checking {url}')
            with urlopen(url, context=context) as file:
                data = json.load(file)
                for info in data['eligibles']:
                    if info['identity'] == eth_address.lower():
                        return info
        return None

    print()
    merkle_info = get_merkle_info()
    print()

    if merkle_info is None:
        print(f'address {eth_address} not found in Merkle tree')
        return

    amount: str = merkle_info['amount']
    if '.' in amount:
        whole, decimal = amount.split('.')
    else:
        whole, decimal = amount, ''
    balance: int = int(whole + decimal + ('0' * (18 - len(decimal))))

    merkle_index: str = merkle_info['merkle_index']
    len_merkle_path: int = merkle_info['merkle_path_len']
    merkle_path: list[str] = merkle_info['merkle_path']
    assert (len_merkle_path == len(merkle_path))

    print('payableAmount')
    print('------------------------------')
    print('0.0001')
    print()
    print('toAddress')
    print('------------------------------')
    print('0x026942155437167f8a18c2602637e30d636f0ce7a88d5ed465f8d1f08f1ea015')
    print()
    print('selector')
    print('------------------------------')
    print('0x00828430c65c40cba334d4723a4c5c02a62f612d73d564a1c7dc146f1d0053f9')
    print()
    print('payload')
    print('------------------------------')
    print(f'"{eth_address}", "{balance}", 0, {merkle_index}, {len_merkle_path}', end=', ')
    print(', '.join([f'"{node}"' for node in merkle_path]), end=', ')
    print(f'"{starknet_address}"')


if __name__ == '__main__':
    main()
