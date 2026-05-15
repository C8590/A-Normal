# Project Plan

## Goal

`ashare-alpha-lab` is an A-share individual stock research system. The MVP focuses on offline research, backtesting, signal generation, and reporting.

The project must never place real orders, connect to broker APIs, hardcode secrets, or claim guaranteed returns.

## MVP Scope

- A-share individual stock research.
- Main-board stocks first.
- Daily and low-frequency workflows.
- Local CSV sample data first.
- Rule-based scoring first.
- Backtesting with realistic Chinese A-share constraints.
- Every signal must include a Chinese `reason`.

## Exclusions

- Live trading.
- Broker integration.
- High-frequency trading.
- Web scraping without explicit instruction.
- Deep learning or complex NLP.
- Secrets, API keys, or any order submission function.

## Milestones

1. Project initialization, documentation, minimal CLI, linting, and tests.
2. Data schema and local CSV loader.
3. Universe filters with Chinese exclusion reasons.
4. Rule-based factor and scoring pipeline from config.
5. Backtest engine with MVP trading constraints.
6. Report generation with risk disclosure.

## Current Universe Builder

The current universe builder creates `universe_daily` from local CSV data and config. It filters board scope, ST and *ST risk, delisting risk, suspension, new listings, insufficient history, low liquidity, one-lot affordability, and recent negative events. It is a research screen only and does not create signals or orders.
