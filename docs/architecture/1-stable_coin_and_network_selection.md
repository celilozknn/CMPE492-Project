## Network and Stablecoin Selection Rationale

The selection of networks and stablecoins was guided by two constraints: maintaining technical feasibility within a 8-9 weeks timeline and ensuring meaningful coverage of global stablecoin activity.

To preserve architectural consistency and reduce implementation overhead, the project focuses only on EVM-compatible networks. This enables a unified ERC-20 event extraction pipeline and comparable graph modeling across chains. The selected networks are:

- Ethereum
- Arbitrum
- Polygon
- Avalanche
- Optimism

Ethereum serves as the primary issuance and liquidity hub. Arbitrum and Optimism represent major Layer 2 rollups, Polygon provides high transaction density, and Avalanche offers an independent EVM Layer 1. Together, they provide structural diversity while keeping the technical stack uniform.

Tron was excluded despite its high USDT volume because it is not EVM-compatible and would require a separate data retrieval architecture. Hedera was similarly excluded due to architectural differences and lower stablecoin relevance within the chosen scope. Given the project timeframe, consistency and feasibility were prioritized.

The selected stablecoins are:

- USDT 
- USDC
- DAI
- XAUT

USDT and USDC dominate global stablecoin volume. DAI introduces a decentralized issuance model, and XAUT provides exposure to commodity-backed stable assets. EUR- or TRY-pegged stablecoins were not included due to significantly lower market dominance and cross-chain activity on the selected networks.

This configuration balances analytical relevance, diversity, and implementation practicality within the defined project scope.