# AGENTS.md

## Project

This repository builds `ashare-alpha-lab`, an A-share individual stock quantitative research system.

The system is for research, backtesting, signal generation, and reporting only.
It must not place real orders.
It must not connect to broker APIs in the MVP.
It must not claim guaranteed returns.
It must not hardcode secrets or API keys.

## Core scope

MVP scope:
- A-share individual stock research system
- Main-board stocks first
- Exclude ChiNext, Beijing Stock Exchange, STAR Market, ST, *ST, delisting-risk stocks, suspended stocks, and newly listed stocks
- Daily / low-frequency research
- Local CSV sample data first
- Rule-based scoring first
- Backtesting with realistic Chinese A-share constraints

## Non-goals for MVP

Do not implement:
- Live trading
- Broker integration
- High-frequency trading
- Web scraping without explicit instruction
- Deep learning
- Complex NLP
- Secrets or API keys
- Any function that directly submits an order

## Engineering rules

- Use Python.
- Put source code under `src/ashare_alpha`.
- Use pytest for tests.
- Use ruff for linting.
- Prefer small, testable modules.
- Avoid hardcoded trading rules.
- Trading rules must be loaded from config files.
- All public functions should have type hints.
- Handle missing data safely.
- Every filter must output a human-readable reason.
- Every trading signal must output a Chinese human-readable reason.
- Do not add secrets, API keys, or credentials to code, configs, docs, or tests.

## Trading rules to model

The system must support:
- T+1
- 100-share lot size
- 0.01 CNY A-share price tick
- price limits
- ST / *ST special risk
- suspension
- limit-up buy failure
- limit-down sell failure
- commission rate
- minimum commission
- stamp tax on sell side
- slippage
- cash and position constraints

## Definition of done

A task is done only when:
- Code is implemented
- Tests are added or updated
- `pytest` passes
- `ruff check` passes
- README or docs are updated if behavior changes
- No live trading code is introduced
