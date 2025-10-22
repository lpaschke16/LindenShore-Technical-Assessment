# Linden Shore Technical Assessment

## Uniswap v3 Liquidity Imbalance & Arbitrage Signal Tracker

Samples Uniswap v3 USDC/WETH pools (0.05% & 0.30%) through the **Ethereum JSON-RPC API**.

This project connects to the Ethereum Mainnet via a free public RPC endpoint (https://ethereum-rpc.publicnode.com) and uses the JSON-RPC API to query **Uniswap v3** liquidity pool state data directly on-chain.

When the primary script, **univ3_arb_tracker.py** is run, it continuously samples two Uniswap v3 liquidity pools for the same pair, **USDC/WETH**, with different fee tiers (0.05% and 0.3%). This data is used to measure:
- Cross-pool price deviations (arbitrage/MEV opportunites)
- Time-Weighted Average Price (TWAP) deviations. or short-term mean-reversion signals
- Liquidity depth and active ticks.

All data sampled from the script is stored locally in a CSV file for later analysis.

## How to Run the Code

### 1. Set up Environment
- Python ≥ 3.8
- ```pip install -r requirements.txt```

### 2. Configure the RPC
In **config.json**, set the Ethereum endpoint to the RPC.
Ex:
```
{
    "ETH_RPC": "https://ethereum-rpc.publicnode.com",
    "ETH_RPC_BACKUP": ["https://rpc.ankr.com/eth/2bd88d0b1410a01dc69088770efb89b5e3af7648f2882ae7c5abcd01e1f63483"],
    "POOLS": {
      "USDC_WETH_005": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
      "USDC_WETH_03":  "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"
    },
    "SAMPLE_INTERVAL_SECONDS": 5,
    "RUN_DURATION_MINUTES": 1,
    "OUTPUT_PATH": "./data/univ3_snapshots.csv"
  }
```
Note: I list two separate endpoints here for resilience in case one fails

### 3. Run the tracker
From the **src/** directory, run:
```python univ3_arb_tracker.py```

If run successfully, you should see console output like this:
```
Connected to chain 1 at block 23629307
Sampled at 2025-10-21T23:49:28.486854+00:00
Price A = 0.000258, Price B = 0.000258
Cross Dev = 0.0123%
TWAP Dev A = 0.0518%, TWAP Dev B = 0.0095%
...
Successfully saved to ./data/univ3_snapshots.csv
```

Results will be stored in the specified CSV file


## What Data the Script Collects
Each row in ***univ3_snapshots.csv*** corresponds to one on-chain snapshot containing the following columns:

| Column                                                  | Description                                     |
| ------------------------------------------------------- | ----------------------------------------------- |
| **timestamp**                                           | UTC time of observation                         |
| **poolA_address / poolB_address**                       | 0.05 % and 0.30 % Uniswap v3 pool addresses     |
| **symbol_pair**                                         | Trading pair (USDC/WETH)                        |
| **fee_a / fee_b**                                       | Fee tier percentages                            |
| **priceA_token1_per_token0 / priceB_token1_per_token0** | Spot price from each pool (token 1 per token 0) |
| **twapA_tick / twapB_tick**                             | 5-minute TWAP prices                            |
| **twap_deviation_a / twap_deviation_b**                 | % deviation between spot and TWAP               |
| **cross_pool_deviation**                                | % price difference across fee tiers             |
| **liquidityA / liquidityB**                             | In-range liquidity values                       |
| **tickA / tickB**                                       | Current tick index (discrete price step)        |

## What I Learned from the Data
### 1. Market Efficiency Across Fee Tiers
After analyzing the data, it is clear that the cross-pool deviations consistently stayed within the range of 0.01 - ~0.15%, which is much less than the combined fee spread of 0.35%. This indicates that Ethereum's Uniswap pools are **tightly arbitraged** and highly efficient 

### 2. Mean-Reversion Around TWAP
TWAP deviations averaged to values near zero, which confirms that Uniswap v3 prices revert quickly to their recent averages. This is an indicator of high liquidity and efficient price discovery on the chain.

### 3. Liquidity effects Volatility
In the data, when **liquidityA** or **liquidityB** dipped temporarily, cross-pool deviations widened consequently. This indicates that lower liquidity (in range) allows for greater short term disorder, which is consistent with well-known market theories.

### 4. Infrastructure
Using public **RPC endpoints** is sufficient for light analytics when including retry logic to catch instances of failed connections. On the other hand, I experimented with more in-depth Ethereum node connection methods, like running a local **Geth** node to host my own RPC endpoint on my local host. This method, and many similar methods using other technologies listed in https://ethereum.org/developers/docs/nodes-and-clients/, are more suitable for higher-frequency work. It was more straightforward to use the public RPC, so I opted for that method.

## References
- Ethereum JSON-RPC Spec: ethereum.org/developers/docs/apis/json-rpc
- Uniswap v3 documentation: https://docs.uniswap.org/
- Public RPC Endpoints: PublicNode and Ankr

  






