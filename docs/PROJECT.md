# Project record

## Objective

Inject faults into outbound calls in tests: wrap sync or async callables with rules that raise, delay through an injected sleep or return canned values, on deterministic triggers.

## Scope

The package is a public-OSS Python library with import name `fault_injector` and no runtime dependencies outside the Python standard library. In scope: `FaultPlan`, `Rule`, `Raise`, `Return`, `Delay`, `Injection`, and `FaultError` as documented in [README.md](../README.md), including sync and async wrapping, rule triggers, seeded probability, injected sleep callables, bounded history, drop counting, event callbacks without call arguments, and `patch` context-manager restoration.

Out of scope: network-level faults (proxies), HTTP status simulation, chaos in production, and patching by import path strings.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | 1919240 / 100700 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.1142 |

## Factory run u295 (measured from API usage)

| Date (UTC) | Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| 2026-11-11 | generation | deepseek-v4-pro | yes | 4856 | 12106 | 0 | 0 | 0.0272 |
| 2026-11-11 | fix-1 | deepseek-flash | no | 25607 | 40622 | 0 | 1148416 | 0.0317 |
| 2026-11-11 | fix-2 | deepseek-flash | no | 13292 | 4046 | 0 | 102400 | 0.0047 |
| 2026-11-11 | fix-3 | deepseek-flash | no | 7790 | 1776 | 0 | 35328 | 0.0023 |
| 2026-11-11 | audit | deepseek-flash | no | 29640 | 26486 | 0 | 414464 | 0.0216 |
| 2026-11-11 | fix-4 | deepseek-flash | no | 7717 | 653 | 0 | 22400 | 0.0016 |
| 2026-11-11 | docs | deepseek-flash | no | 107074 | 15011 | 0 | 256 | 0.0251 |

Total: $0.1142. Prices: deepseek line, as measured by its adapter. Providers serve the current version of each model id, so the date tells which version answered; versions, launch stages and price sources per line are in the factory's model register (docs/MODELS.md).
