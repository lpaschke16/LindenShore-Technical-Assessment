"""
LindenShore Technical Assessment - Uniswap v3 Liquidity Imbalance and Arbitrage Signal Tracker

This script samples two Uniswap v3 pools for the same pair but different fee tiers
(ex: USDC/WETH 0.05% and 0.30%) via Ethereum JSON-RPC. It records spot price
(slot0.sqrtPriceX96), a 5-minute Time Weighted Average Price (from observe()), cross-pool price
deviation (a DEX arbitrage cue), and spot–TWAP deviations (a microstructure/
mean-reversion cue), along with in-range liquidity and ticks. The results are saved to a CSV file.

By: Lucas Paschke
"""


import json
import time
import pandas as pd
from web3 import Web3
from datetime import datetime, timedelta, timezone
from decimal import Decimal, getcontext
import os

## Initialization
getcontext().prec = 40
ROOT = os.path.dirname(os.path.abspath(__file__))

def q_96():
    """Returns the Q96 fixed-point scaling factor (2**96).

    Uniswap v3 stores sqrt (price) in Q64.96 fixed-point format. Conversions usually
    require the exact integer value of 2**96 as a `Decimal` to maintain precision.

    Returns:
        Decimal: The value 2**96 as a high-precision Decimal.

    """
    return Decimal(2) ** 96



def load_config():
    """
    - Loads the configuration file. 
    -If it doesn't exist, it loads the example configuration file.
    -Returns the configuration as a dictionary (JSON object).

    """
    cfg = os.path.join(ROOT, 'config.json')
    if os.path.exists(cfg):
        with open(cfg, 'r') as f:
            return json.load(f)
    with open(os.path.join(ROOT, 'config.example.json'), 'r') as f:
        return json.load(f)

def price_from_sqrt_price_x96(sqrt_price_x96, decimals_0, decimals_1, invert=False):
    """
    Converts a Uniswap v3 'sqrt_price_x96' price  to an interpretable price.
    
    Args:
        sqrt_price_x96: The sqrt price from the Uniswap v3 pool.
        decimals_0: The decimal precision (ERC20) of the first token.
        decimals_1: The decimal precision (ERC20) of the second token.
        invert: Whether to invert the price (token 1 per token 0 or token 0 per token 1)
    Returns:
        The interpretable price as a Decimal (ensures high precision).
    """

    ratio = (Decimal(sqrt_price_x96) ** 2) / (q_96() ** 2) # Note Decimal(2) ** 96 == q_96()
    scale = Decimal(10) ** (decimals_0 - decimals_1)
    p1_per_p0 = ratio * scale # token 1 per token 0
    return (Decimal(1) / p1_per_p0) if invert else p1_per_p0 # token 0 per token 1 if invert is True

def connect_web3_client(rpc_url):
    """
    Connects to a Web3 client using the provided RPC URL.
    Args:
        rpc_url: The HTTP RPC URL of the Ethereum endpoint.
    Returns:
        web.Web3: A Web3 client object if the connection is successful, otherwise None.
    """
    try:
        return Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
    except Exception as e:
        print(f"Error connecting to Web3 client: {e}")
        return None

def load_abi(name):
    """
    Small helper to load a contract ABI JSON by logical name from `src/abi/` directory.
    Args:
        name: The name of the ABI file
    Returns:
        dict: The ABI as a dictionary compatible with web3.eth.contract
    """

    with open(os.path.join(ROOT, 'abi', f'{name}.json'), 'r') as f:
        return json.load(f)

def get_pool_view(w3, pool_address):
    """
    Binds a Uniswap v3 liquidity pool and organizes essential metadata for run funciton.
    Specifically, this function will construct:
        1) A typed liquidity pool object using the Uniswap v3 Pool ABI
        2) Token0 and Token1 contract objects using the ERC20 ABI to read symbol and decimals
        3) Liquidity pool metadata (address, fee, tick spacing, etc...)

    Args:
        w3 (web3.Web3): A connected Web3 client object.
        pool_address: (string): Liquidity pool contract address, a hex string

    Returns:
        dict: A dictionary containing the following metadata (keys):
            1) 'pool' (Contract): Bound Liquidiy pool contract
            2) 'token0' (dict): Token0 contract object in the form {"address": <address>, "symbol": <symbol>, "decimals": <decimals>}
            3) 'token1' (dict): Token1 contract object in the form {"address": <address>, "symbol": <symbol>, "decimals": <decimals>}
            4) 'fee' (int): Liquidity pool fee
            5) 'tick_spacing' (int): Liquidity pool tick granularity

    Example usage:
        >>> w3 = Web3(Web3.HTTPProvider(w3, '0xA3b5E8C9F10D4726B09A1cE4d5F82e73B6A940C1')
        >>> view["token0"]["symbol"], view["token1"]["symbol"], view["fee"]
            ('USDC', 'WETH', 500)

    """

    pool = w3.eth.contract(address = Web3.to_checksum_address(pool_address), abi = load_abi('univ3_pool'))
    
    token0_address = pool.functions.token0().call()
    token1_address = pool.functions.token1().call()

    erc20 = load_abi('erc20')

    token0 = w3.eth.contract(address = token0_address, abi = erc20)
    token1 = w3.eth.contract(address = token1_address, abi = erc20)

    symbol0 = token0.functions.symbol().call()
    symbol1 = token1.functions.symbol().call()
    decimals0 = token0.functions.decimals().call()
    decimals1 = token1.functions.decimals().call()
    fee = pool.functions.fee().call()
    tick_spacing = pool.functions.tickSpacing().call()
    
    return {
        "pool": pool,
        "token0": {"address": token0.address, "symbol": symbol0, "decimals": decimals0},
        "token1": {"address": token1.address, "symbol": symbol1, "decimals": decimals1},
        "fee": fee,
        "tick_spacing": tick_spacing
    }

def compute_twap(pool, window_seconds = 300):
    """
    Computes a Time Weighted Average Price (TWAP) over a specified window.
    Uses the Uniswap v3 Pool ABI's 'observe' function to fetch price and liquidity changes over time.
    Note: TWAP_tick = (tick_cumulative_now - tick_cumulative_then) - one window

    Args:
        pool (Contract): Bound Uniswap v3 Liquidity pool contract
        window_seconds (int): Lookback window in seconds (default: 300 or 5 mins)

    Returns:
        int: The average tick over the window

    """
    (ticks, seconds) = pool.functions.observe([window_seconds, 0]).call()
    tick_start, tick_end = ticks[0], ticks[1]
    twap = (tick_end - tick_start) // window_seconds
    return int(twap)

def tick_to_price(tick, decimals_0, decimals_1, invert=False):
    """
    Converts a Uniswap v3 'tick' to an interpretable price.

    Important Note: In Uniswap v3, tick spacing is fixed at a constant ratio of 1.0001.
                    So, price = (1.0001 ** tick) * (10 ** (decimal_0 - decimal_1))

    Args:
        tick (int): Tick index
        decimals_0 (int): Decimal precision (ERC20) of the first token
        decimals_1 (int): Decimal precision (ERC20) of the second token
        invert (bool): Whether to invert the price (token 1 per token 0 or token 0 per token 1)

    Returns:
        Decimal: The price corresponding to the tick, as a Decimal (ensures high precision)
    """

    base = Decimal('1.0001') ** Decimal(tick)
    scale = Decimal(10) ** (decimals_0 - decimals_1)
    p1_per_p0 = base * scale
    return (Decimal(1) / p1_per_p0) if invert else p1_per_p0

def run():
    """
    Main sampling and signal generation loop: connect Web3, query liquidity pools, find signals, and save results in CSV

    Workflow:
        1) Load configuration (RPC URL, pool addresses, cadence, duration, output path)
        2) Connect to Etherium JSON-RPC and bind two Uniswap v3 liquidity pools for the same pair
           but different fee tiers (ex: 0.05% and 0.30%)
        
        3) for each dame interval of SAMPLE_INTERVAL_SECONDS until RUN_DURATION_MINUTES, do the following:
            - Read spot state from each pool's slot0
            - Compute 5 minute TWAP tick using observe([300, 0]) and convert to price using tick_to_price()
            - Compute signals:
                * cross_pool_deviation: price gap across fee tiers (arbitrage cue)
                * twap_deviation_a, twap_deviation_b: spot vs TWAP deviations (mean-reversion cue)

            - Append a record with timestamp, prices, TWAPs, ticks, liquidity, and signals
        
        4) Save observations to CSV file at OUTPUT_PATH

    Output: 
        CSV file at OUTPUT_PATH with columns:

        timestamp, poolA_address, poolB_address, symbol_pair, fee_a, fee_b,
        priceA_token1_per_token0, priceB_token1_per_token0, twapA_tick, twapB_tick,
        twap_deviation_a, twap_deviation_b, cross_pool_deviation, liquidityA, liquidityB, tickA, tickB
    """

    # Load config and set up parameters
    config = load_config()
    rpc = config["ETH_RPC"]
    pools = config["POOLS"]
    output_path = config["OUTPUT_PATH"]
    interval_seconds = int(config.get("SAMPLE_INTERVAL_SECONDS", 15))
    duration_minutes = int(config.get("RUN_DURATION_MINUTES", 5))

    # Connect to Web3
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    w3 = connect_web3_client(rpc)
    if not w3:
        raise Exception("Failed to connect to Web3 client")
    # small checks to see if connection works
    chain_id = w3.eth.chain_id
    block_number = w3.eth.block_number
    print(f"Connected to chain {chain_id} at block {block_number}")



    # Two fee tiers per pair (0.05% and 0.30%)
    view_a = get_pool_view(w3, pools["USDC_WETH_005"])
    view_b = get_pool_view(w3, pools["USDC_WETH_03"])

    rows = []
    end_time = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)

    # main loop
    while datetime.now(timezone.utc) < end_time:
        time_stamp = datetime.now(timezone.utc).isoformat()

        # Pool 1 @ 0.05%
        slot0_a = view_a["pool"].functions.slot0().call()
        sqrt_price_x96_a = slot0_a[0]
        tick_a = slot0_a[1]
        liquidity_a = view_a["pool"].functions.liquidity().call()
        price_a = price_from_sqrt_price_x96(sqrt_price_x96_a, view_a["token0"]["decimals"], view_a["token1"]["decimals"])
        twap_a = compute_twap(view_a["pool"], window_seconds = 300)
        twap_price_a = tick_to_price(twap_a, view_a["token0"]["decimals"], view_a["token1"]["decimals"])

        # Pool 2 @ 0.30%
        slot0_b = view_b["pool"].functions.slot0().call()
        sqrt_price_x96_b = slot0_b[0]
        tick_b = slot0_b[1]
        liquidity_b = view_b["pool"].functions.liquidity().call()
        price_b = price_from_sqrt_price_x96(sqrt_price_x96_b, view_b["token0"]["decimals"], view_b["token1"]["decimals"])
        twap_b = compute_twap(view_b["pool"], window_seconds = 300)
        twap_price_b = tick_to_price(twap_b, view_b["token0"]["decimals"], view_b["token1"]["decimals"])
        
        # Calculate signals
        # % Diff between pools
        cross_pool_deviation = (price_a - price_b) / ((price_a + price_b) / 2) * 100
        twap_deviation_a = ((price_a - twap_price_a) / twap_price_a)* 100
        twap_deviation_b = ((price_b - twap_price_b) / twap_price_b)* 100
        
        # Fill out rows
        rows.append({
            "timestamp": time_stamp,
            "poolA_address": view_a["pool"].address,
            "poolB_address": view_b["pool"].address,
            "symbol_pair": f"{view_a['token0']['symbol']}/{view_a['token1']['symbol']}",
            "fee_a": view_a["fee"] / 100,
            "fee_b": view_b["fee"] / 100,
            "priceA_token1_per_token0": str(price_a),
            "priceB_token1_per_token0": str(price_b),
            "twapA_tick": str(twap_price_a),
            "twapB_tick": str(twap_price_b),
            "twap_deviation_a": float(twap_deviation_a),
            "twap_deviation_b": float(twap_deviation_b),
            "cross_pool_deviation": float(cross_pool_deviation),
            "liquidityA": int(liquidity_a),
            "liquidityB": int(liquidity_b),
            "tickA": tick_a,
            "tickB": tick_b
        })

        print(f"Sampled at {time_stamp}\n")
        print(f"Price A = {price_a:.6f}, Price B = {price_b:.6f}\n")
        print(f"Cross Dev = {cross_pool_deviation:.4f}%\n") 
        print(f"TWAP Dev A = {twap_deviation_a:.4f}%, TWAP Dev B = {twap_deviation_b:.4f}%")

        time.sleep(interval_seconds)
    
    # Save to CSV
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    print(f"Successfully saved to {config['OUTPUT_PATH']}")
        

## Run the script!
if __name__ == "__main__":
    run()
    
    
    