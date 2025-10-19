# LindenShore-Technical-Assessment

## Uniswap v3 Liquidity Imbalance & Arbitrage Signal Tracker

This tool samples two **Uniswap v3 USDC/WETH** pools on Ethereum (0.05% & 0.30%) and logs:
- Spot price from `slot0.sqrtPriceX96`
- 5-minute TWAP from `observe([300, 0])`
- Spot–TWAP deviation (mean-reversion signal)
- Cross-pool price deviation (intra-DEX arbitrage cue)
- Liquidity (context for slippage)

### Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/univ3_arb_tracker.py
