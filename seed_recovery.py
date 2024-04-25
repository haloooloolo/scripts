#!/usr/bin/env python3

from eth_account.hdaccount import Mnemonic, key_from_seed
from eth_utils import is_hex_address, is_same_address
from eth_typing import HexAddress
from eth_keys import keys
from bitarray import bitarray
from bitarray.util import int2ba
from hashlib import sha256

from typing import Optional, Iterable, cast


M = Mnemonic('english')
NUM_WORDS = 24
DERIVATION_PATH = "m/44'/60'/0'/0/0"


def get_words_by_prefix(prefix: str) -> list[str]:
    return [w for w in M.wordlist if w.startswith(prefix)]


def parse() -> tuple[list[str], HexAddress]:
    while not is_hex_address(address := input('wallet address: ').strip()):
        print('Not a valid ETH address, try again')

    bip39 = set(M.wordlist)

    def read_seed_word(prompt: str) -> Optional[str]:
        word_raw = input(prompt).strip().lower()
        if word_raw in bip39:
            return word_raw

        candidates = get_words_by_prefix(word_raw)
        if len(candidates) == 1:
            print(f'({candidates[0]})')
            return candidates[0]

        return None

    words = []
    for i in range(NUM_WORDS):
        while not (word := read_seed_word(f'{i+1}: ')):
            print('Not a valid BIP39 word, try again')
        words.append(word)

    return words, cast(HexAddress, address)


def strategy_1(known_words: list[str]) -> Iterable[list[str]]:
    mnemonic = [w for w in known_words]

    print()
    print('Swapping word pairs...')
    for i in range(NUM_WORDS):
        for j in range(i+1, NUM_WORDS):
            print(f'{i+1} <-> {j+1}')
            mnemonic[i], mnemonic[j] = mnemonic[j], mnemonic[i]
            yield mnemonic
            mnemonic[i], mnemonic[j] = mnemonic[j], mnemonic[i]


def strategy_2(known_words: list[str]) -> Iterable[list[str]]:
    mnemonic = [w for w in known_words]

    print()
    print('Replacing single words...')
    for i in range(NUM_WORDS):
        for j, word in enumerate(M.wordlist):
            print(f'{i+1}/{NUM_WORDS} - {j+1}/{len(M.wordlist)}')
            mnemonic[i] = word
            yield mnemonic
        mnemonic[i] = known_words[i]


def strategy_3(known_words: list[str]) -> Iterable[list[str]]:
    mnemonic = [w for w in known_words]

    print()
    print('Replacing word pairs...')
    for i in range(NUM_WORDS):
        words_i = get_words_by_prefix(known_words[i][0])
        for k, wi in enumerate(words_i):
            mnemonic[i] = wi
            for j in range(i+1, NUM_WORDS):
                words_j = get_words_by_prefix(known_words[j][0])
                for l, wj in enumerate(words_j):
                    print(f'{i+1}/{NUM_WORDS} - {k+1}/{len(words_i)}', end=', ')
                    print(f'{j+1}/{NUM_WORDS} - {l+1}/{len(words_j)}')
                    mnemonic[j] = wj
                    yield mnemonic

                mnemonic[j] = known_words[j]
        mnemonic[i] = known_words[i]


def recover(known_words: list[str], address: HexAddress) -> Optional[list[str]]:
    arr_repr = {word: int2ba(idx, length=11) for (idx, word) in enumerate(M.wordlist)}
    entropy_size = 8 * (4 * NUM_WORDS // 3)

    def is_match(mnemonic: list[str]) -> bool:
        def is_valid() -> bool:
            encoded_seed = bitarray()
            for word in mnemonic:
                encoded_seed.extend(arr_repr[word])

            checksum = bitarray()
            checksum.frombytes(sha256(encoded_seed[:entropy_size].tobytes()).digest())
            checksum = checksum[:(len(encoded_seed) - entropy_size)]
            return encoded_seed[entropy_size:] == checksum

        if not is_valid():
            return False

        seed = M.to_seed(' '.join(mnemonic), '')
        private_key = key_from_seed(seed, DERIVATION_PATH)
        public_key = keys.PrivateKey(private_key).public_key
        return is_same_address(public_key.to_address(), address)

    if is_match(known_words):
        return known_words

    strategies = (strategy_1, strategy_2, strategy_3)

    for strategy in strategies:
        for permutation in strategy(known_words):
            if is_match(permutation):
                return permutation

    return None


def main(known_words: list[str], address: HexAddress) -> None:
    print('Trying to recover mnemonic...')
    mnemonic = recover(known_words, address)

    def colorize(txt: str, color: int) -> str:
        return f'\033[{color}m{txt}\033[0m'

    print()
    if not mnemonic:
        print('Recovery failed.')
        return

    print('Found matching mnemonic!')
    for i in range(NUM_WORDS):
        if mnemonic[i] == known_words[i]:
            print(f'{i+1}. {colorize(mnemonic[i], 32)}')
        else:
            print(f'{i+1}. {colorize(known_words[i], 31)} -> {colorize(mnemonic[i], 32)}')


if __name__ == '__main__':
    try:
        main(*parse())
    except KeyboardInterrupt:
        print()
        print('Recovery canceled.')
