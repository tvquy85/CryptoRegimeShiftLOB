# L2 Snapshot Replay Executable Specification

This specification describes the replay implemented in
`src/simulator/market_order_sim.py`. It is a visible-depth L2 snapshot
approximation for benchmark diagnostics. It is not a live execution model, not a
passive order-fill model, and not an exact L3 queue-priority reconstruction.

## Inputs

For each candidate signal index `i`, the simulator reads:

- `actions[i]`: `+1` for buy/long entry, `-1` for sell/short entry, `0` to abstain.
- `mid_price`.
- Twenty visible bid levels: `bid_0_price`, `bid_0_size`, ..., `bid_19_price`, `bid_19_size`.
- Twenty visible ask levels: `ask_0_price`, `ask_0_size`, ..., `ask_19_price`, `ask_19_size`.
- Optional reporting columns: `event_time`, `regime`.

Default benchmark constants are:

| Parameter | Default | Meaning |
|---|---:|---|
| `latency_events` | `1` | Entry snapshot index shift after a signal. |
| `fee_bps` | `1.0` | Explicit taker-style fee in basis points. |
| `spread_multiplier` | `1.0` | Stress multiplier for distance from mid to quoted price. |
| `depth_multiplier` | `1.0` | Stress multiplier for visible size. |
| `partial_fill` | `true` | Whether partial fills can be accepted. |
| `min_fill_ratio` | `0.5` | Minimum fill ratio required at both entry and exit. |
| `trade_notional` | `1000.0` | Requested notional used to compute target quantity. |
| `cooldown_events` | `3` | Minimum event-index gap between accepted entries. |

## Timing Rule

For a nonzero signal at row `i`:

```text
entry_index = i + latency_events
exit_index  = entry_index + hold_events
```

The trade is skipped if entry or exit falls outside the simulator-valid replay
range or if `entry_index - last_accepted_entry_index < cooldown_events`.
Latency is an event-index shift only; there is no wall-clock interpolation.

## Target Quantity

The requested quantity is computed from requested notional and the entry or exit
snapshot mid price:

```text
q_target = trade_notional / max(mid_price, 1e-9)
```

The entry and exit sweeps each compute their own target quantity from the
snapshot they consume. The final trade quantity is the matched quantity:

```text
q = min(entry_filled_quantity, exit_filled_quantity)
```

## Market Buy Sweep

A market buy consumes visible ask levels from `ask_0` to `ask_19`.

For level `l`:

```text
transformed_price_l = mid_price + spread_multiplier * (ask_l_price - mid_price)
transformed_size_l  = ask_l_size * depth_multiplier
x_l = min(remaining_quantity, transformed_size_l)
```

Nonfinite, nonpositive, or missing deeper-level price/size values are treated as
unavailable depth for that level. They are not imputed.

## Market Sell Sweep

A market sell consumes visible bid levels from `bid_0` to `bid_19`.

For level `l`:

```text
transformed_price_l = mid_price - spread_multiplier * (mid_price - bid_l_price)
transformed_size_l  = bid_l_size * depth_multiplier
x_l = min(remaining_quantity, transformed_size_l)
```

Spread crossing is implicit: buys execute on asks and sells execute on bids.

## VWAP, Fill Ratio, and Slippage

For the filled levels:

```text
filled_quantity = sum_l x_l
vwap_price      = sum_l x_l * transformed_price_l / filled_quantity
fill_ratio      = filled_quantity / q_target
slippage        = abs(vwap_price - best_transformed_price)
```

If `filled_quantity == 0`, the sweep returns a zero fill.

## Partial Fill and Depth Exhaustion

The simulator computes separate entry and exit fills.

- If `partial_fill=true`, a trade is accepted only when both entry and exit
  fill ratios are at least `min_fill_ratio`.
- If `partial_fill=false`, any sweep with `fill_ratio < 1.0` is converted to a
  zero fill, causing the trade to be skipped.
- If visible depth is exhausted before the requested quantity is reached, the
  above partial-fill rule decides whether the trade is kept or skipped.

## Fee and PnL

Fees are charged on matched filled notional, not requested notional:

```text
entry_fee = fee_bps / 10000 * q * entry_vwap
exit_fee  = fee_bps / 10000 * q * exit_vwap
total_fee = entry_fee + exit_fee
```

Long trade:

```text
gross_pnl = q * (exit_sell_vwap - entry_buy_vwap)
net_pnl   = gross_pnl - total_fee
```

Short trade:

```text
gross_pnl = q * (entry_sell_vwap - exit_buy_vwap)
net_pnl   = gross_pnl - total_fee
```

The reported `total_cost` column is the explicit fee total. The implicit spread
crossing and depth effects enter through the entry/exit VWAP prices.

## Invalid Books and Missing Columns

The simulator fails fast if required replay columns are absent.

The simulator treats a row as zero-fill if the top of book is invalid:

- nonfinite or nonpositive `mid_price`;
- nonfinite or nonpositive best bid/ask prices;
- nonfinite or nonpositive best bid/ask sizes;
- crossed best book where `bid_0_price > ask_0_price`.

The benchmark pipeline normally removes invalid and crossed best books before
feature generation. These simulator rules are defensive checks for reproducible
replay behavior.

## Boundary

This replay is deliberately limited to snapshot-level visible depth. It does not
model hidden liquidity, exchange queue priority, passive limit-order fills,
order cancellation races, venue routing, or live latency.
