# Security Spec

## 1. security.yaml

`configs/ashare_alpha/security.yaml` defines the safety boundary for future external data sources:

```yaml
offline_mode: true
allow_network: false
allow_broker_connections: false
allow_live_trading: false
```

It also defines secret policy, network policy, and per-source security metadata. API keys are never stored directly. A source that needs a key stores only the environment variable name, such as `ASHARE_ALPHA_TUSHARE_TOKEN`.

## 2. Offline And Network Policy

`offline_mode=true` means any future network call must be blocked. `allow_network=false` is a second explicit switch that also blocks network access. Both defaults are intentionally conservative.

Future real adapters must call `NetworkGuard.assert_network_allowed(source_name, domain)` before any network access. Broker connections and live trading are separately guarded by `assert_broker_connection_allowed()` and `assert_live_trading_allowed()`.

## 3. Secrets

API keys and tokens must be provided through environment variables. Config files may contain only the variable name, not the value.

Allowed safe form:

```yaml
api_key_env_var: ASHARE_ALPHA_TUSHARE_TOKEN
```

Unsafe form:

```yaml
api_key: plain-secret-value
```

The secret provider reads only `os.environ`. It does not read `.env` files or secret files. CLI output uses redaction and must not print raw secret values.

## 4. check-security

Scan config YAML/JSON files for suspicious plaintext secrets and unsafe live-trading flags:

```bash
python -m ashare_alpha check-security
python -m ashare_alpha check-security --format json
python -m ashare_alpha check-security --config-dir configs/ashare_alpha --output-dir outputs/security/manual
```

Outputs:

```text
security_scan_report.json
security_scan_report.md
```

The scanner skips `.git`, `outputs`, and `data` directories.

## 5. check-secrets

Check whether configured secret environment variables are present without printing their values:

```bash
python -m ashare_alpha check-secrets
python -m ashare_alpha check-secrets --format json
```

Disabled data sources do not fail when their secret env var is unset. Enabled sources that require an API key fail if the env var is missing.

## 6. show-network-policy

Show the active offline/network policy:

```bash
python -m ashare_alpha show-network-policy
python -m ashare_alpha show-network-policy --format json
```

The output includes offline mode, network permission, broker/live-trading flags, allowed domains, timeout, retry count, enabled data sources, and sources that would require network access.

## 7. Data Source Security Summary

`list-data-sources` includes security status:

```bash
python -m ashare_alpha list-data-sources
```

`inspect-data-source` includes a per-source security section:

```bash
python -m ashare_alpha inspect-data-source --name local_csv
```

For sources with `api_key_env_var`, the detail view shows whether the environment variable is set, but not its raw value.

## 8. Pipeline Security Check

`run-pipeline` does not run security checks by default, preserving existing behavior. Enable it explicitly:

```bash
python -m ashare_alpha run-pipeline --date 2026-03-20 --check-security
```

When enabled, a `security_check` step runs before `validate_data`. Error-level findings fail the pipeline. Warning and info findings allow it to continue.

## 9. Current Boundary

The current system remains offline. It does not call external APIs, scrape websites, import Tushare or AkShare SDKs, connect to brokers, or submit live orders. It is a research, backtesting, signal, and reporting system only, and it is not investment advice.

Any future real data-source adapter must pass through `NetworkGuard` and keep secrets in environment variables.
