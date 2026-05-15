# Risk Spec

## Research-only Boundary

The system is for research, backtesting, signal generation, and reporting only.

It must not:

- Place real orders.
- Connect to broker APIs.
- Store hardcoded secrets or API keys.
- Claim guaranteed returns.
- Present output as investment advice.

## MVP Risk Filters

- Exclude ChiNext, Beijing Stock Exchange, STAR Market, ST, *ST, delisting-risk, suspended, and newly listed stocks unless config later says otherwise.
- Treat missing or suspicious fields conservatively.
- Emit a Chinese reason for every exclusion and signal.
- Keep all trading constraints and thresholds in config files.

## Reporting Disclosure

Reports must include a clear Chinese risk disclosure that results are for research only and do not guarantee returns.

## Universe Boundary

`universe_daily` is only a research eligibility screen. A stock being allowed into the universe is not a buy recommendation, does not imply expected returns, and must not trigger live orders.
