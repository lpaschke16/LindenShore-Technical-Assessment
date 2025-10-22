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

## Why This Dataset was Selected
Uniswap v3 represents an advanced decentralized market structure in the Ethereum ecosystem.  Unlike traditional order book structures, Uniswap pools are automated market makers that rely on liquidity curves and constant product pricing. In Uniswap v3 specifically, liquidity providers can concentrate their capital within specific price ranges, which creates multiple overlapping micro-markets for the same pair of assets. This introduces the concept of liquidity imbalances, in which situations where one fee tier or tick range has a slightly different price relative to another. 

The USDC and WETH pair was chosen because it is one of the most liquid and actively arbitraged pairs on Ethereum. By tracking two Uniswap v3 pools for the same pair but with different fee tiers, I can directly observe how price equilibrium forms across parallel automated market makers and how arbitrageurs and liquidity conditions interact in real time. This data set was particularly interesting for a variety of reasons. The first was that it captures pure, on-chain market data, as I was able to make a direct connection to the chain using RPC. This procedure was entirely new for me going into this project, so it was very interesting to set up for the first time. Second, this dataset allowed me to directly measure arbitrage efficiency, liquidity depth, and mean-reversion through the Uniswap smart contracts themselves. Lastly, it provided insights into Maximal Extractable Value (MEV) activity by quantifying the micro-price deviations that commonly incentivise on-chain searchers. All in all, this dataset was both theoretically interesting and practically useful for revealing decentralized market microstructures and designing useful trading strategies that interact with on-chain liquidity. 

## What I Learned from the Data
When running the script for longer time intervals, the data shows that the two Uniswap v3 pools, USDC and WETH (0.05% and 0.3% fee tiers) maintain extremely close prices, typically within 0.01% - 0.15% of each other. This narrow range shows the efficiency of Uniswap v3 and the way liquidity and arbitrage work on the Ethereum chain.

### 1. Market Efficiency Across Fee Tiers
After analyzing the data, it is clear that the cross-pool deviations consistently stayed within the range of 0.01 - ~0.15%, which is much less than the combined fee spread of 0.35%. This indicates that Ethereum's Uniswap pools are **tightly arbitraged** and highly efficient. Each pool is an independent liquidity venue for the same asset pair, but are constantly monitored by professional market makers and arbitrage trackers on centralized exchanges. When one pool becomes slightly cheaper or more expensive than another, they seemigly instantaneously execute quick swaps to restore uniformity. Since both pools use concentrated liquidity, the price impact of a single trade is small, so arbitrage opportunities quickly collapse after a few seconds. The price deviations between pools that I observed confirm that the pools are being continuously balanced by on-chain market activity. 

### 2. Time-Weighted Average Price (TWAP) Deviation
The TWAP deviation data reveals the short-term dynamics of Uniswap's liquidity. A TWAP represents a smoothed averaged price over a defined window (I used a 5 minute window). When the current spot price equals the TWAP, it means prices are currently stable. When spot price diverges from TWAP, it suggests temporary buying or selling pressure. In my data, the TWAP deviations hovered around zero with slight fluctations of around $\pm$0.05%. This indicates that short-term price shocks are quickly absorbed and prices revert to their average quickly. This is evidence of a mean-reverting stucture, which is what is expected in a liquid pair like USDC and WETH where many arbitrageurs and market makers compete. 

### 3. Liquidity affects Volatility
In the data, when **liquidityA** or **liquidityB** dipped temporarily, cross-pool deviations widened consequently. This indicates that lower liquidity (in range) allows for greater short term disorder. This makes sense intuitively, as liquidity providers often pull capital or when large trades consume liquidity in a specific tick range, each additional trade will move the price further. This will widen the gap between fee tiers until arbitrage closes it again. In other words, liquidity is seemingly acting as a buffer, where the deeper the pool is, the tighter the price alignment across fee tiers will be. 

### 4. Arbitrage
The cross-pool deviations I recorded are much below the combined cost of trading through both pools. This means that, although these dislocations are observable, they are not profitable for direct arbitrage by a trader under any normal circumstances. Instead, they illustrate the embedded micro-inefficiencies that are exploited using certain techniques when deviations briefly exceed that threshold. In other words, this tracker is effectively detecting the same type of transient inefficiencies that on-chain searchers, like Maximal Extracable Value (MEV) consistently monitor. 

### 4. Infrastructure
Using public **RPC endpoints** is sufficient for light analytics when including logic to catch instances of failed connections. On the other hand, I experimented with more in-depth Ethereum node connection methods, like running a local **Geth** node to host my own RPC endpoint on my local host. This method, and many similar methods using other technologies listed in https://ethereum.org/developers/docs/nodes-and-clients/, are more suitable for higher-frequency work. It was more straightforward to use the public RPC, so I opted for that method.

### Summary
From a broader perspective, the dataset demonstrates how Uniswap v3's design of multiple fee tiers and concetrated liquidity influences price behavior. Each fee tier attracts different types of liquidity providers, as 0.05% is used for higher-volume, lower-volatility pairs, while 0.3% is for more volatile conditions. Despite their differences, they both respond almost identically to market movements. The very small price difference I measured confirms that even though liquidity is distributed across different pools, the market collectively prices assets as if there was a single, unified order book.

In summary, this project shows:
- Ethereum's decentralized markets are extremely efficient, with arbitrage keeping Uniswap v3's fee tiers tightly synchronized
- Uniswap's TWAP mechanism produces a stable, mean-reverting reference price that quickly corrects temporary order-flow imbalances
- Liquidity governs how far prices can temporarily drift before arbitrage resores uniformity.
- Observing and quantifying these deviations provides a window into the hidden mechanics of MEV, market efficiency, and liquidity health in decentralized finance.

## Potential Applications

### Arbitrage and Execution Optimization
The tracker's cross-pool deviation metric can be integrated into algorithmic trading systems to indentify mis-pricings between Uniswap pools or between Uniswap and centralized exchanges. By setting the thresholds to certain values, you could back test profitability and latency requirements for on-chain arbitrage detectors.

### MEV Detection Monitoring
Persistent or unusually large deviations signal periods of MEV congestion or reduced arbitrage participation. Monitoring these metrics can help quantify network-wide arbitrage intensity measures or signal when blocks include multiple bundles.

### Liquidity Optimization
Liquidity providers can use this data to determine which fee tiers offer more stable pricing and lower impermanent loss. By observing how liquidity depth correlates with volatility and price alignment, liquidity providers can optimize their capital allocations to balance risk and yield.

### Risk and Market Micro-Structure Analysis
Traders and researchers can use this framework to evaluate:
- How liquidity fragmentation across fee tiers affects volatility
- Resiliency of automatic market makers under periods of high stress
- Responsiveness of TWAP oracles that construct many DeFi lending and liquidation mechanisms.

## References
- Ethereum JSON-RPC Spec: https://ethereum.org/developers/docs/apis/json-rpc
- Uniswap v3 documentation: https://docs.uniswap.org/
- Public RPC Endpoints: PublicNode and Ankr

  






