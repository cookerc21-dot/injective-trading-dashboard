"""Trading strategy engine with live prices (CoinGecko) + backtesting."""
import os
import json
import time
import hashlib
from datetime import datetime, timedelta
import requests

# ─── Asset definitions ────────────────────────────────────────────────
ASSETS = {
    "INJ": {
        "name": "Injective",
        "coingecko_id": "injective-protocol",
        "decimals": 18,
        "type": "L1 Token",
    },
    "USDT": {
        "name": "Tether",
        "coingecko_id": "tether",
        "decimals": 6,
        "type": "Stablecoin",
    },
    "stINJ": {
        "name": "Staked Injective",
        "coingecko_id": "staked-injective",
        "decimals": 18,
        "type": "Liquid Staking",
    },
    "BTC": {
        "name": "Bitcoin",
        "coingecko_id": "bitcoin",
        "decimals": 8,
        "type": "L1 Token",
    },
    "ETH": {
        "name": "Ethereum",
        "coingecko_id": "ethereum",
        "decimals": 18,
        "type": "L1 Token",
    },
    "ATOM": {
        "name": "Cosmos",
        "coingecko_id": "cosmos",
        "decimals": 6,
        "type": "L1 Token",
    },
}

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(key: str) -> str:
    h = hashlib.md5(key.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.json")


def _cache_get(key: str, ttl_seconds: int = 60) -> dict | None:
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        if time.time() - data.get("_ts", 0) > ttl_seconds:
            return None
        return data.get("payload")
    except Exception:
        return None


def _cache_set(key: str, payload: dict):
    path = _cache_path(key)
    try:
        with open(path, "w") as f:
            json.dump({"_ts": time.time(), "payload": payload}, f)
    except Exception:
        pass


# ─── Live data helpers ────────────────────────────────────────────────

def fetch_price(asset_id: str) -> dict | None:
    """Fetch current price + 24h change from CoinGecko."""
    info = ASSETS.get(asset_id)
    if not info:
        return None
    cg_id = info["coingecko_id"]
    cache_key = f"price:{cg_id}"
    cached = _cache_get(cache_key, ttl_seconds=30)
    if cached:
        return cached
    try:
        url = (
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={cg_id}&vs_currencies=usd&include_24hr_change=true"
        )
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json().get(cg_id, {})
        result = {
            "asset": asset_id,
            "usd": data.get("usd"),
            "change_24h": data.get("usd_24h_change"),
            "updated_at": datetime.utcnow().isoformat(),
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        return None


def fetch_historical(
    asset_id: str, days: int = 7
) -> list[dict]:
    """Fetch OHLCV candles from CoinGecko."""
    info = ASSETS.get(asset_id)
    if not info:
        return []
    cg_id = info["coingecko_id"]
    cache_key = f"history:{cg_id}:{days}"
    cached = _cache_get(cache_key, ttl_seconds=300)
    if cached:
        return cached
    try:
        url = (
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc"
            f"?vs_currency=usd&days={days}"
        )
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return []
        raw = r.json()  # [[timestamp_ms, open, high, low, close], ...]
        candles = []
        for c in raw:
            candles.append({
                "timestamp": datetime.fromtimestamp(c[0] / 1000).isoformat(),
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
            })
        _cache_set(cache_key, candles)
        return candles
    except Exception:
        return []


# ─── Backtesting engine ──────────────────────────────────────────────

BACKTEST_STRATEGIES = {
    "sma_crossover": {
        "name": "SMA Crossover",
        "params": {"fast_period": 10, "slow_period": 30},
        "description": "Buy when fast SMA crosses above slow SMA. Sell when it crosses below.",
    },
    "rsi_mean_reversion": {
        "name": "RSI Mean Reversion",
        "params": {"rsi_period": 14, "oversold": 30, "overbought": 70},
        "description": "Buy when RSI is oversold, sell when overbought.",
    },
    "macd": {
        "name": "MACD",
        "params": {"fast": 12, "slow": 26, "signal": 9},
        "description": "Buy when MACD crosses above signal line, sell when below.",
    },
    "bollinger_breakout": {
        "name": "Bollinger Breakout",
        "params": {"period": 20, "std_dev": 2},
        "description": "Buy when price touches lower band, sell at upper band.",
    },
}


def _sma(data: list[float], period: int) -> list[float | None]:
    if len(data) < period:
        return [None] * len(data)
    result = [None] * (period - 1)
    for i in range(period - 1, len(data)):
        result.append(sum(data[i - period + 1 : i + 1]) / period)
    return result


def _rsi(data: list[float], period: int) -> list[float | None]:
    if len(data) < period + 1:
        return [None] * len(data)
    result = [None] * period
    for i in range(period, len(data)):
        gains = losses = 0
        for j in range(i - period + 1, i + 1):
            diff = data[j] - data[j - 1]
            if diff >= 0:
                gains += diff
            else:
                losses -= diff
        avg_gain = gains / period
        avg_loss = losses / period
        if avg_loss == 0:
            result.append(100)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))
    return result


def _ema(data: list[float], period: int) -> list[float | None]:
    if len(data) < period:
        return [None] * len(data)
    multiplier = 2 / (period + 1)
    result = [None] * (period - 1)
    ema = sum(data[:period]) / period
    result.append(ema)
    for i in range(period, len(data)):
        ema = (data[i] - ema) * multiplier + ema
        result.append(ema)
    return result


def _macd(data: list[float], fast: int, slow: int, signal: int) -> tuple:
    ema_fast = _ema(data, fast)
    ema_slow = _ema(data, slow)
    macd_line = []
    for i in range(len(data)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line.append(ema_fast[i] - ema_slow[i])
        else:
            macd_line.append(None)
    signal_line = _ema([x for x in macd_line if x is not None], signal)
    # Pad signal_line to match length
    signal_padded = [None] * (len(macd_line) - len(signal_line)) + signal_line
    histogram = []
    for i in range(len(data)):
        if macd_line[i] is not None and signal_padded[i] is not None:
            histogram.append(macd_line[i] - signal_padded[i])
        else:
            histogram.append(None)
    return macd_line, signal_padded, histogram


def run_backtest(
    asset_id: str,
    strategy_id: str,
    days: int = 30,
    params: dict | None = None,
    capital: float = 1000.0,
) -> dict:
    """Run a full backtest and return performance metrics."""
    candles = fetch_historical(asset_id, days)
    if not candles:
        return {"error": f"No historical data for {asset_id}"}

    closes = [c["close"] for c in candles]
    timestamps = [c["timestamp"] for c in candles]
    strat = BACKTEST_STRATEGIES.get(strategy_id)
    if not strat:
        return {"error": f"Unknown strategy: {strategy_id}"}

    merged_params = {**strat["params"], **(params or {})}

    # Generate signals
    signals = [0] * len(closes)  # 1=buy, -1=sell, 0=hold

    if strategy_id == "sma_crossover":
        fast_period = int(merged_params.get("fast_period", 10))
        slow_period = int(merged_params.get("slow_period", 30))
        fast_sma = _sma(closes, fast_period)
        slow_sma = _sma(closes, slow_period)
        for i in range(1, len(closes)):
            if fast_sma[i] is not None and slow_sma[i] is not None:
                if fast_sma[i - 1] is not None and slow_sma[i - 1] is not None:
                    if fast_sma[i - 1] <= slow_sma[i - 1] and fast_sma[i] > slow_sma[i]:
                        signals[i] = 1  # Buy
                    elif fast_sma[i - 1] >= slow_sma[i - 1] and fast_sma[i] < slow_sma[i]:
                        signals[i] = -1  # Sell

    elif strategy_id == "rsi_mean_reversion":
        period = int(merged_params.get("rsi_period", 14))
        oversold = float(merged_params.get("oversold", 30))
        overbought = float(merged_params.get("overbought", 70))
        rsi_values = _rsi(closes, period)
        for i in range(1, len(closes)):
            if rsi_values[i] is not None:
                if rsi_values[i - 1] is not None:
                    if rsi_values[i - 1] <= oversold and rsi_values[i] > oversold:
                        signals[i] = 1
                    elif rsi_values[i - 1] >= overbought and rsi_values[i] < overbought:
                        signals[i] = -1

    elif strategy_id == "macd":
        fast = int(merged_params.get("fast", 12))
        slow = int(merged_params.get("slow", 26))
        signal = int(merged_params.get("signal", 9))
        macd_line, signal_line, histogram = _macd(closes, fast, slow, signal)
        for i in range(1, len(closes)):
            if macd_line[i] is not None and signal_line[i] is not None:
                if macd_line[i - 1] is not None and signal_line[i - 1] is not None:
                    if macd_line[i - 1] <= signal_line[i - 1] and macd_line[i] > signal_line[i]:
                        signals[i] = 1
                    elif macd_line[i - 1] >= signal_line[i - 1] and macd_line[i] < signal_line[i]:
                        signals[i] = -1

    elif strategy_id == "bollinger_breakout":
        period = int(merged_params.get("period", 20))
        std_mult = float(merged_params.get("std_dev", 2))
        sma = _sma(closes, period)
        upper = [None] * len(closes)
        lower = [None] * len(closes)
        for i in range(period - 1, len(closes)):
            if sma[i] is not None:
                window = closes[i - period + 1 : i + 1]
                variance = sum((x - sma[i]) ** 2 for x in window) / period
                std = variance ** 0.5
                upper[i] = sma[i] + std_mult * std
                lower[i] = sma[i] - std_mult * std
        for i in range(1, len(closes)):
            if lower[i] is not None and upper[i] is not None:
                if (lower[i-1] is None or closes[i-1] > lower[i-1]) and closes[i] <= lower[i]:
                    signals[i] = 1
                elif (upper[i-1] is None or closes[i-1] < upper[i-1]) and closes[i] >= upper[i]:
                    signals[i] = -1

    # Simulate trading
    cash = capital
    position = 0.0
    trades = []
    for i in range(len(closes)):
        price = closes[i]
        if signals[i] == 1 and cash > 0:  # Buy
            position = cash / price
            trades.append({
                "timestamp": timestamps[i],
                "type": "buy",
                "price": price,
                "size": cash,
                "units": position,
            })
            cash = 0
        elif signals[i] == -1 and position > 0:  # Sell
            cash = position * price
            trades.append({
                "timestamp": timestamps[i],
                "type": "sell",
                "price": price,
                "size": cash,
                "units": position,
            })
            position = 0

    # Final value
    final_value = cash + (position * closes[-1] if position > 0 else 0)
    total_return = ((final_value - capital) / capital) * 100

    # Calculate equity curve
    equity_curve = []
    running_cash = capital
    running_position = 0.0
    for i in range(len(closes)):
        if signals[i] == 1 and running_cash > 0:
            running_position = running_cash / closes[i]
            running_cash = 0
        elif signals[i] == -1 and running_position > 0:
            running_cash = running_position * closes[i]
            running_position = 0
        equity = running_cash + (running_position * closes[i] if running_position > 0 else 0)
        equity_curve.append({
            "timestamp": timestamps[i],
            "equity": round(equity, 2),
            "signal": signals[i],
        })

    # Win rate
    winning_trades = 0
    closed_trades = []
    for i in range(0, len(trades) - 1, 2):
        if i + 1 < len(trades):
            buy_t = trades[i]
            sell_t = trades[i + 1]
            pnl_pct = ((sell_t["price"] - buy_t["price"]) / buy_t["price"]) * 100
            closed_trades.append({
                "buy_time": buy_t["timestamp"],
                "sell_time": sell_t["timestamp"],
                "buy_price": buy_t["price"],
                "sell_price": sell_t["price"],
                "pnl_pct": round(pnl_pct, 2),
            })
            if pnl_pct > 0:
                winning_trades += 1

    # Max drawdown
    peak = capital
    max_dd = 0
    for point in equity_curve:
        if point["equity"] > peak:
            peak = point["equity"]
        dd = ((peak - point["equity"]) / peak) * 100
        if dd > max_dd:
            max_dd = dd

    return {
        "asset": asset_id,
        "strategy": strategy_id,
        "strategy_name": strat["name"],
        "params": merged_params,
        "days": days,
        "capital": capital,
        "final_value": round(final_value, 2),
        "total_return_pct": round(total_return, 2),
        "total_trades": len(trades),
        "winning_trades": winning_trades,
        "win_rate": round((winning_trades / max(len(closed_trades), 1)) * 100, 1),
        "max_drawdown_pct": round(max_dd, 2),
        "trades": closed_trades[-20:],  # last 20 closed trades
        "equity_curve": equity_curve[:: max(1, len(equity_curve) // 200)],  # downsampled
        "signals": [
            {"timestamp": timestamps[i], "signal": signals[i], "price": closes[i]}
            for i in range(len(closes))
            if signals[i] != 0
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }
