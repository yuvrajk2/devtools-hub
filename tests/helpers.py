from datetime import datetime

import app as appmod


def prime_rates(rates=None):
    """Fill the rate cache so tests never touch the network."""
    appmod._rates.update(
        at=datetime.now().timestamp() + 10 ** 7, retry=0.0, stale=False,
        updated="Fri, 30 Oct 2026 00:00:00 +0000",
        rates=rates or {"EUR": 1.0, "USD": 2.0, "GBP": 0.5, "JPY": 150.0, "NPR": 160.0})
