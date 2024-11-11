#!/usr/bin/env python3

import ssl
import json
from urllib.request import urlopen

from typing import Optional, Union


def is_hex_addr(address: str, target_len: int) -> bool:
    try:
        int(address, 16)
    except ValueError:
        return False

    prefix = '0x'
    return address.startswith(prefix) and (len(address) - len(prefix) == target_len)


def read_hex_addr(addr_type: str, target_len: int) -> str:
    def read() -> str:
        return input(f'{addr_type} address: ').strip().lower()

    while not is_hex_addr(addr := read(), target_len):
        print(f'not a valid {addr_type} address, try again')

    return addr


def main() -> None:
    eth_address = read_hex_addr('ETH', 40)
    starknet_address = read_hex_addr('Starknet', 64)

    target_address = '0x026942155437167f8a18c2602637e30d636f0ce7a88d5ed465f8d1f08f1ea015'
    assert is_hex_addr(target_address, 64)
    selector_address = '0x00828430c65c40cba334d4723a4c5c02a62f612d73d564a1c7dc146f1d0053f9'
    assert is_hex_addr(selector_address, 64)

    def get_merkle_info() -> Optional[dict[str, Union[str, list, int]]]:
        print()
        context = ssl._create_unverified_context()
        for i in range(10):
            merkle_url = f'https://raw.githubusercontent.com/starknet-io/provisions-data/main/eth/eth-{i}.json'
            print(f'checking {merkle_url}')
            with urlopen(merkle_url, context=context) as file:
                data = json.load(file)
                for info in data['eligibles']:
                    if info['identity'] == eth_address:
                        return info
        return None

    merkle_info = get_merkle_info()

    print()
    if merkle_info is None:
        print(f'{eth_address} not found in Merkle tree')
        return

    amount: str = merkle_info['amount']
    if '.' in amount:
        whole, decimal = amount.split('.')
    else:
        whole, decimal = amount, ''
    balance: int = int(whole + decimal + ('0' * (18 - len(decimal))))

    merkle_index: int = int(merkle_info['merkle_index'])
    len_merkle_path: int = merkle_info['merkle_path_len']
    merkle_path: list[str] = merkle_info['merkle_path']
    assert (len_merkle_path == len(merkle_path))

    def quote(_param: Union[str, int]) -> str:
        return f'"{_param}"'

    payload: list[str] = []
    payload.extend(map(quote, (eth_address, balance)))
    payload.extend(map(str, (0, merkle_index, len_merkle_path)))
    payload.extend(map(quote, merkle_path))
    payload.extend(map(quote, (starknet_address,)))

    print('payableAmount')
    print('------------------------------')
    print('0.0001')
    print()
    print('toAddress')
    print('------------------------------')
    print(target_address)
    print()
    print('selector')
    print('------------------------------')
    print(selector_address)
    print()
    print('payload')
    print('------------------------------')
    print(', '.join(payload))


if __name__ == '__main__':
    main()
