"""The decision core of the highball AI. Pure functions, no network.

Beliefs come in (error tables plus the trailing bias from the training
log), a board of bands with live quotes comes in, and orders come out.
Every rule here is registered in SPEC.md. The desk and the replay both
call exactly this code, which is what makes the replay a real test.
"""

import math

MIN_EV_CENTS = 5      # entry needs at least this much edge after fees
MIN_ASK = 10          # longshot filter, registered: never buy under 10c
MAX_ASK = 90          # nothing left to win above this
EXIT_MARGIN = 5       # sell when bid >= model probability + margin
HARVEST_BID = 90      # or when bid >= this with the day still young
HARVEST_BEFORE_HOUR = 12
TRAIL = 30
MIN_BIAS_N = 10
QTY = 100             # flat sim size, contracts per position


def taker_fee_cents(price_cents):
    """Kalshi quadratic taker fee per contract, rounded up to the cent."""
    p = price_cents / 100.0
    return math.ceil(7 * p * (1 - p))


def season(date):
    return "warm" if 5 <= int(date[5:7]) <= 9 else "cold"


def bias(history_errors):
    """Trailing mean error, the AI's learned station correction.

    history_errors: chronological list of (actual - forecast) floats
    for one city and lead, everything known strictly before today.
    """
    tail = history_errors[-TRAIL:]
    if len(tail) < MIN_BIAS_N:
        return 0.0
    return sum(tail) / len(tail)


def band_prob(table, f_corrected, lo, hi):
    """Probability the official high lands in [lo, hi] given the
    corrected forecast. lo=None means an or-below tail (high < hi+1),
    hi=None means an or-above tail (high > lo)."""
    r = round(f_corrected)
    p = table["p"]
    clip = max(int(e) for e in p)
    total = 0.0
    for e_str, prob in p.items():
        a = r + int(e_str)
        if lo is not None and hi is not None:
            inside = lo <= a <= hi
        elif lo is not None:
            inside = a > lo
            if int(e_str) == clip:      # tail mass beyond the clip
                inside = inside or (lo < r + clip)
        else:
            inside = a < hi
            if int(e_str) == -clip:
                inside = inside or (hi > r - clip)
        if inside:
            total += prob
    return min(1.0, total)


def price_board(table, f_corrected, bands):
    """Attach a model probability to every band on the board.

    bands: [{"ticker", "lo", "hi", "bid", "ask"}] with cents or None.
    Returns the same list with "p_model" (cents scale, 0..100).
    """
    out = []
    for b in bands:
        p = band_prob(table, f_corrected, b.get("lo"), b.get("hi"))
        nb = dict(b)
        nb["p_model"] = round(p * 100, 1)
        out.append(nb)
    return out


def pick_entry(priced_board):
    """Best positive-EV band on the board, or None.

    EV per contract = model probability - ask - taker fee. The
    longshot filter and the top cap are registered rules.
    """
    best = None
    for b in priced_board:
        ask = b.get("ask")
        if ask is None or not (MIN_ASK <= ask <= MAX_ASK):
            continue
        ev = b["p_model"] - ask - taker_fee_cents(ask)
        if ev >= MIN_EV_CENTS and (best is None or ev > best["ev"]):
            best = dict(b)
            best["ev"] = round(ev, 1)
    return best


def should_exit(bid, p_model, local_hour):
    """The registered exit rule. Returns (True, reason) or (False, "")."""
    if bid is None:
        return False, ""
    if bid >= p_model + EXIT_MARGIN:
        return True, "edge_gone"
    if bid >= HARVEST_BID and local_hour < HARVEST_BEFORE_HOUR:
        return True, "harvest"
    return False, ""


def entry_pnl(ask, won):
    """Hold-to-settle P&L per contract in cents, both fee assumptions."""
    fee = taker_fee_cents(ask)
    taker = (100 - ask - fee) if won else (-ask - fee)
    maker = (100 - ask) if won else (-ask)
    return taker, maker


def sell_pnl(ask, bid):
    """P&L per contract when sold before settlement."""
    taker = bid - ask - taker_fee_cents(ask) - taker_fee_cents(bid)
    maker = bid - ask
    return taker, maker


SLIPPAGE_CAP = 5  # never chase more than this past the decision price


def fill_walk(levels, qty, limit_price=None):
    """Walk the real book like a real order would.

    levels: [(price_cents, size), ...] best price first (asks ascending
    to buy, bids descending to sell). Fills up to qty, refusing any
    level past limit_price. Returns (vwap_cents, filled_qty). A sim
    fill is only as honest as the depth it consumed, so partial fills
    are returned as partial, never rounded up.
    """
    filled = 0
    cost = 0.0
    for price, size in levels:
        if limit_price is not None and price > limit_price:
            break
        take = min(size, qty - filled)
        if take <= 0:
            break
        filled += take
        cost += take * price
    if filled == 0:
        return None, 0
    return round(cost / filled, 2), filled
