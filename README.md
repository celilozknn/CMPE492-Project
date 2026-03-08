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

## Contact

For questions, feedback, or collaboration inquiries, please reach out via GitHub Issues or email.

**Celil Özkan**  
celil.ozkan@std.bogazici.edu.tr
