# LindenShore-Technical-Assessment

## Uniswap v3 Liquidity Imbalance & Arbitrage Signal Tracker

Samples Uniswap v3 USDC/WETH pools (0.05% & 0.30%) through the **Ethereum JSON-RPC API**.

The script uses `web3.py`, which sends the same JSON-RPC calls described at
[ethereum.org/developers/docs/apis/json-rpc](https://ethereum.org/developers/docs/apis/json-rpc/)
— for example:
- `eth_call` to read smart-contract state (`slot0`, `observe`, `liquidity`)
- `eth_blockNumber` to confirm connectivity

### Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/univ3_arb_tracker.py
