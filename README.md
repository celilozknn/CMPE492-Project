# Stablecoin Flow Analysis on Blockchains

Undergraduate Final Year Project  
Department of Computer Engineering  
Boğaziçi University  

**Student:** Celil Özkan 
**Supervisor:** Prof. Can Özturan  

## Overview

This project aims to analyze stablecoin transaction flows across multiple blockchain networks.

We will construct a dataset of selected stablecoin contracts and extract token transfer data from EVM-compatible chains. Using this data, we plan to build graph-based models to study transaction flows, address interactions, and cross-network movement patterns.

The project combines:

- Blockchain data retrieval
- Graph-based analysis
- Address classification
- Basic visualization and reporting

## Initial Scope

Planned networks include:

- Ethereum
- Polygon
- Arbitrum
- Avalanche

Planned stablecoins include:

- USDT
- USDC
- DAI
- XAUT

Scope may evolve as the project progresses.

## Project Phases

The work is organized into three main stages:

1. Fetch – Collect and store stablecoin transfer data  
2. Analysis – Build graph models and compute metrics  
3. Report – Interpret findings and present results  

## Development Guidelines

### Branching Convention

- `main` – Stable project state
- `feat/<short-description>` – New functionality
- `fix/<short-description>` – Bug fixes
- `refactor/<short-description>` – Code improvements, changes
- `chore/<short-description>` – Unimportant changes (e.g., formatting)

All major work should be developed in a separate branch and merged into `main` after validation.

## Database

We use PostgreSQL 16 via Docker.

### 1. Environment

Create a `.env` file:

```env
POSTGRES_DB=<your_database_name>
POSTGRES_USER=<your_database_user>
POSTGRES_PASSWORD=<your_database_password>
POSTGRES_PORT=<your_host_port>
```

### 2. Starting the Database

Run the following command to start the PostgreSQL container:

```bash 
docker compose up -d
```

- This will create the database and user.
- Uses a persistent Docker volume for data.

### 3. Connecting to the Database

Use the following command to connect to the database:

```bash
docker exec -it <container_name> psql -U <your_database_user> -d <your_database_name>
```

### 4. Creating Tables

You should also create the necessary tables, which can be done via SQL commands. You can find sql scripts in the `sql` directory. 
I didn't want to bother with ORM for now, so you can run raw SQL commands using the `psql` command line interface or any PostgreSQL client.

### How to run 

#### To fetch data:

If you don't want to specify a spesific block range you can use --auto. This will learn what was saved in the database as the last block and start fetching from there. This is useful for continuous data collection for automated server. Possible <network_name> values are: ethereum, polygon, optimism, arbitrum, avalanche. You can also write --manual and specify the block range with --start and --end flags. You can learn start and end block numbers for each network from the respective block explorers. For example, for Ethereum you can use Etherscan, for Polygon you can use Polygonscan, etc.

```bash
python3 src/cli.py fetch --network <network_name> --auto
python3 src/cli.py fetch --network <network_name> --manual --start <start_block> --end <end_block>
```

Examples:
```bash
python3 src/cli.py fetch --network ethereum --auto
python3 src/cli.py fetch --network ethereum --manual --start 24620000 --end 24622559
```

## Contact

For questions, feedback, or collaboration inquiries, please reach out via GitHub Issues or email.

**Celil Özkan**  
celil.ozkan@std.bogazici.edu.tr
