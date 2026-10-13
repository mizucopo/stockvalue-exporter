"""Deterministic quote data shared by the fixture and its quality checks."""


def price_for(symbol: str) -> float:
    """Return a stable, nonzero price without relying on Python's hash seed."""
    return float(100 + sum((index + 1) * ord(c) for index, c in enumerate(symbol)))


def quote_for(symbol: str) -> dict[str, object]:
    """Match the Yahoo fields used by the unchanged production fetcher."""
    price = price_for(symbol)
    return {
        "currentPrice": price,
        "previousClose": price - 1,
        "longName": f"Fixture {symbol}",
        "currency": "USD",
        "exchange": "NMS",
        "volume": 1000,
        "marketCap": 1000000,
    }
