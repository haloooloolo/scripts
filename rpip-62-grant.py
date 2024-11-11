#!/usr/bin/env python3

import math
import argparse

from tqdm import tqdm
from web3 import Web3
from multicall import Call

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--rpc')
    parser.add_argument('-b', '--block', type=int)
    parser.add_argument('-p', '--previous-payouts', type=float)
    parser.add_argument('-v', '--verify-baseline', action='store_true')
    return parser.parse_args()

def from_wei(amount: int) -> float:
    return amount / 1e18

def get_minipool_split(_neth: int, _peth: int) -> tuple[int, int]:
    num_leb8 = int((_peth - _neth) / 16)
    num_eb16 = int((3*_neth - _peth) / 32)
    return num_leb8, num_eb16

def main(args):
    rpc_url = args.rpc or "http://localhost:8545"
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    baseline_block = 21060412
    current_block = args.block or w3.eth.get_block('latest').number

    previous_payout = args.previous_payouts or 0.0
    
    SUPERNODE = '0x2A906f92B0378Bb19a3619E2751b1e0b8cab6B29'
    NODE_MANAGER = '0x2b52479F6ea009907e46fc43e91064D1b92Fdc86'
    NODE_STAKING = '0xF18Dc176C10Ff6D8b5A17974126D43301F8EEB95'
    NETWORK_PRICES = '0x25E54Bf48369b8FB25bB79d3a3Ff7F3BA448E382'

    def call(address: str, function: str, args: list, block: int):
        return Call(address, [function] + args, block_id=block, _w3=w3)()

    def get_eth_provided(node_addr: str, block: int) -> int:
        return int(from_wei(call(NODE_STAKING, 'getNodeETHProvided(address)(uint256)', [node_addr], block)))

    def get_eth_matched(node_addr: str, block: int) -> int:
        return int(from_wei(call(NODE_STAKING, 'getNodeETHMatched(address)(uint256)', [node_addr], block)))

    def get_eth_split(block: int) -> tuple[int, int]:
        neth, peth = 0, 0
        node_count = call(NODE_MANAGER, 'getNodeCount()(uint256)', [], block)
        for node_idx in tqdm(range(node_count), desc=f"state @ {block:,}", leave=False):
            node_addr = call(NODE_MANAGER, 'getNodeAt(uint256)(address)', [node_idx], block)
            neth += get_eth_provided(node_addr, block)
            peth += get_eth_matched(node_addr, block)

        return neth, peth

    if args.verify_baseline:
        neth_baseline, peth_baseline = get_eth_split(baseline_block)
        neth_baseline -= get_eth_provided(SUPERNODE, baseline_block)
        peth_baseline -= get_eth_matched(SUPERNODE, baseline_block)
    else:
        neth_baseline, peth_baseline = 216_920, 488_680
    leb8_baseline, eb16_baseline = get_minipool_split(neth_baseline, peth_baseline)

    print(f"Baseline Stats (block {baseline_block:,})")
    print(f"------------------------------------------------------------")
    print(f"Total nETH (excl. Constellation): {neth_baseline:,}")
    print(f"Total pETH (excl. Constellation): {peth_baseline:,}")
    print(f"{leb8_baseline:,} LEB8 | {eb16_baseline:,} EB16")
    print(f"")

    neth_current, peth_current = get_eth_split(current_block)
    leb8_current, eb16_current = get_minipool_split(neth_current, peth_current)
    rpl_price = from_wei(call(NETWORK_PRICES, 'getRPLPrice()(uint256)', [], current_block))
    neth_constellation = get_eth_provided(SUPERNODE, current_block)
    peth_constellation = 3 * neth_constellation
    rpl_constellation = from_wei(call(NODE_STAKING, 'getNodeRPLStake(address)(uint256)', [SUPERNODE], current_block))
    neth_constellation_collateralized = min(neth_constellation, 8 * int(math.floor(rpl_constellation * rpl_price / (0.45 * 8))))
    peth_constellation_collateralized = 3 * neth_constellation_collateralized
    leb8_constellation_collateralized = int(neth_constellation_collateralized / 8)

    print(f"Current Stats (block {current_block:,})")
    print(f"------------------------------------------------------------")
    print(f"Total nETH: {neth_current:,}")
    print(f"  of that Constellation: {neth_constellation:,}")
    print(f"    of that collateralized (45%): {neth_constellation_collateralized:,}")
    print(f"Total pETH: {peth_current:,}")
    print(f"  of that Constellation: {peth_constellation:,}")
    print(f"    of that collateralized (15%): {peth_constellation_collateralized:,}")
    print(f"{leb8_current:,} LEB8 | {eb16_current:,} EB16")
    print(f"")

    neth_net_change = neth_current - neth_baseline - neth_constellation_collateralized
    peth_net_change = peth_current - peth_baseline - peth_constellation_collateralized
    leb8_net_change = leb8_current - leb8_baseline - leb8_constellation_collateralized
    eb16_net_change = eb16_current - eb16_baseline

    print(f"Changes")
    print(f"------------------------------------------------------------")
    print(f"+{neth_net_change:,} nETH | +{peth_net_change:,} pETH")
    print(f"+{leb8_net_change:,} LEB8 | {eb16_net_change:,} EB16")
    print(f"")

    grant_limit = 60_000.0
    grant_payout = max(0.0, min(0.6 * neth_net_change + 0.06 * peth_net_change, grant_limit))
    new_payout = max(0.0, grant_payout - previous_payout)
    payout_shares = {
        "haloooloolo": 0.4662,
        "samus      ": 0.1221,
        "knoshua    ": 0.1138,
        "Valdorff   ": 0.0943,
        "Yokem      ": 0.0578,
        "sckuzzle   ": 0.0514,
        "LenOfTawa  ": 0.0373,
        "Ramana     ": 0.0305,
        "Patches    ": 0.0266
    }
    payout_shares = {k: round(new_payout * v, 2) for k, v in payout_shares.items()}
    payout_shares[list(payout_shares.keys())[0]] -= sum(payout_shares.values()) - new_payout

    print(f"Total grant payout: ${grant_payout:,.2f} / ${grant_limit:,.2f}")
    print(f"New payout:         ${new_payout:,.2f}")
    print(f"------------------------------------------------------------")
    for name, payout in payout_shares.items():
        print(f"{name} : ${payout:,.2f}")

if __name__ == '__main__':
    main(parse_args())
