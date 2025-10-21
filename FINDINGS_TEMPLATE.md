```markdown
# Uniswap v3 Liquidity Imbalance & Arbitrage Signal Tracker — Findings

## Why this dataset
Concentrated liquidity in v3 creates temporary microstructure dislocations across fee tiers. We observe them via spot–TWAP and cross-pool gaps.

## Methodology
- Chain: Ethereum (public RPC)
- Pools: USDC/WETH 0.05% and 0.30%
- Cadence: 15s; Duration: 5–60m
- Metrics: spot, 5m TWAP, spot–TWAP deviation, cross-pool deviation, liquidity
- Storage: CSV

## Key insights (replace with your results)
- Cross-pool deviation spikes (e.g., >3 bps) cluster during volatility or thin liquidity.
- Spot–TWAP deviations >5 bps often revert within a few samples.
- Larger gaps align with the lower-liquidity tier.

## Applications
- Intra-DEX arb: trigger when cross-pool gap > fees + gas
- CEX–DEX basis: add CEX mid; trade when edge > costs
- MEV monitoring: find blocks where deviations collapse after swaps

## Limitations & next steps
- Public RPC latency can miss short-lived edges
- Implement exact v3 price-impact math for sizing
- Parse Swap logs; add gas model for executable backtests