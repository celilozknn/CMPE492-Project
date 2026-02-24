# Stablecoin Flow Analysis – Core Blockchain Concepts

## 1. What is a Block?
A block is a container of transactions.  
Each block includes:
- A list of transactions  
- A reference (hash) to the previous block  
- Metadata (timestamp, block number, gas info)

Blocks form a chain by referencing the previous block’s hash.

---

## 2. What is a Transaction?
A transaction is a state-changing operation on the blockchain.

It includes:
- `from` (sender address)
- `to` (recipient address or contract)
- `value` (native coin amount, optional)
- `input data` (function call data for contracts)

For token transfers, the transaction usually calls a smart contract function.

---

## 3. Native Coin vs Token

### Native Coin
- Built into the blockchain protocol.
- Examples: ETH (Ethereum), MATIC (Polygon), AVAX (Avalanche).
- Transfers are direct value movements between addresses.

### Token
- Implemented as a smart contract.
- Stablecoins (USDT, USDC, DAI) are tokens.
- Transfers are function calls to the token contract.

---

## 4. What is ERC-20?
ERC-20 is a token standard on Ethereum defining how tokens behave.

Key functions:
- `transfer(address to, uint amount)`
- `balanceOf(address owner)`
- `approve()`, `transferFrom()`

Key event:
- `Transfer(address from, address to, uint value)`

Stablecoins on Ethereum-compatible chains typically follow ERC-20.

---

## 5. What is ERC-402?
ERC-402 relates to HTTP-based token payments.  
It is not commonly used for stablecoins and is likely not directly relevant to core flow analysis.  
I wanted to put here since Prof Özturan mentioned it and we can analyze this protocol too.

---

## 6. Externally Owned Account (EOA) vs Contract Account

### EOA
- Controlled by a private key.
- Represents users or exchange wallets.
- Can initiate transactions.

### Contract Account
- Contains smart contract code.
- Executes predefined logic.
- Cannot initiate transactions by itself.

Detection method:
- If `eth_getCode(address)` returns empty → EOA
- If code exists → Contract

---

## 7. How Token Balances Work
Tokens are not stored inside user wallets.

Instead:
- The token contract stores balances in its internal state.
- Example:

- balance[adress] = amount


When a transfer happens:
- The contract updates internal balances.
- Emits a `Transfer` event.

---

## 8. What is a Transfer Event?
When tokens move, the contract emits:

Transfer(from, to, amount)


This event is logged in the blockchain.

For flow analysis:
- These events are the primary data source.
- Each event becomes a directed edge in the graph.

---

## 9. Mint and Burn

### Mint
- Creation of new tokens.
- Often represented as:
  - `from = 0x000...000`
  - `to = recipient`
- Increases total supply.

### Burn
- Destruction of tokens.
- Often represented as:
  - `to = 0x000...000`
- Decreases total supply.

Mint/Burn events affect supply and liquidity analysis.

---

## 10. What is a Bridge?
A bridge enables token movement between blockchains.

Process:
1. Tokens are locked on the source chain.
2. Equivalent tokens are minted on the destination chain.

Bridge contracts:
- Hold large token balances.
- Act as liquidity hubs.
- Important nodes in flow graphs.

---

## 11. What is a DEX?
DEX (Decentralized Exchange) is a smart contract enabling token swaps.

Examples:
- Uniswap
- SushiSwap
- PancakeSwap

When swapping:
- User sends tokens to DEX contract.
- Receives another asset in return.

DEX contracts:
- High-volume nodes.
- Often high-centrality in graph analysis.

---

## 12. User–Contract Relationship
In token transfers:
- User calls the token contract.
- The contract updates balances internally.
- Emits a `Transfer` event.

Even though transactions go:

- User → Token Contract

The emitted event represents:

- User A → User B


This allows reconstruction of peer-to-peer flows.

---

## 13. Nodes and Edges for Graph Modeling

### Nodes
- User addresses (EOA)
- Contract addresses (DEX, bridges, token contracts, exchange wallets)

### Edges
- Directed from `sender` → `receiver`
- Weight = token amount
- Timestamp = block time

Graph type:
- Directed
- Weighted
- Time-aware (optional for temporal analysis)

---

## 14. Scope for Stablecoin Flow Analysis
For initial implementation:
- Select major chains (e.g., Ethereum, Polygon, Arbitrum, Avalanche, Tron)
- Select major stablecoins (e.g., USDT, USDC, DAI)
- Extract ERC-20 Transfer events
- Construct directed weighted graphs
- Apply graph algorithms (PageRank, degree centrality, max flow)

This forms the foundation for advanced flow and systemic analysis.