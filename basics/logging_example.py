"""Demo of every logging level writing to a real .log file.

Run it directly:
    python basics/logging_example.py

It processes a tiny batch of orders. The batch is rigged so each level
fires for a real reason instead of a print-style roll call.
"""

import logging
import logging.config
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "app.log"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)-24s | %(funcName)s:%(lineno)d | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "brief": {"format": "%(levelname)-8s %(message)s"},
    },
    "handlers": {
        # level NOTSET (0): the handler writes whatever its logger lets through,
        # which is how DEBUG lines reach the file but not the terminal.
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_FILE),
            "maxBytes": 1_000_000,
            "backupCount": 3,
            "encoding": "utf-8",
            "formatter": "detailed",
            "level": logging.NOTSET,
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "brief",
            "level": logging.INFO,
        },
    },
    "loggers": {
        "shop": {"level": logging.DEBUG, "handlers": ["file", "console"], "propagate": False},
        # No level set, so this one inherits DEBUG from "shop" through the hierarchy.
        "shop.payments": {},
    },
    "root": {"level": logging.WARNING, "handlers": ["file", "console"]},
}

log = logging.getLogger("shop.orders")
pay_log = logging.getLogger("shop.payments")

INVENTORY = {"keyboard": 12, "mouse": 3, "monitor": 0}
LOW_STOCK_THRESHOLD = 5

ORDERS = [
    {"id": "A-1001", "item": "keyboard", "qty": 2, "card": "4111111111111111"},
    {"id": "A-1002", "item": "mouse", "qty": 3, "card": "4111111111111111"},
    {"id": "A-1003", "item": "monitor", "qty": 1, "card": "4111111111111111"},
    {"id": "A-1004", "item": "keyboard", "qty": 1, "card": "bad-card"},
]


class PaymentDeclined(Exception):
    pass


def charge_card(order):
    pay_log.debug("Authorising %s for order %s", order["card"][-4:], order["id"])
    if not order["card"].isdigit():
        raise PaymentDeclined(f"card number is not numeric: {order['card']!r}")
    return f"txn-{order['id']}"


def process_order(order):
    """Return True when the order ships."""
    log.debug("Received order payload: %s", order)

    stock = INVENTORY.get(order["item"], 0)
    if stock < order["qty"]:
        log.error(
            "Order %s cannot ship: %s has %d in stock, %d requested",
            order["id"], order["item"], stock, order["qty"],
        )
        return False

    try:
        txn = charge_card(order)
    except PaymentDeclined:
        # exc_info=True puts the traceback in the log file, where it belongs.
        log.error("Order %s payment failed", order["id"], exc_info=True)
        return False

    INVENTORY[order["item"]] = stock - order["qty"]
    log.info("Order %s shipped (%d x %s, %s)", order["id"], order["qty"], order["item"], txn)

    remaining = INVENTORY[order["item"]]
    if remaining <= LOW_STOCK_THRESHOLD:
        log.warning("Stock low: %s down to %d units", order["item"], remaining)
    return True


def run_batch():
    log.info("Starting batch of %d orders", len(ORDERS))
    shipped = sum(process_order(order) for order in ORDERS)
    failed = len(ORDERS) - shipped

    log.info("Batch finished: %d shipped, %d failed", shipped, failed)
    if failed >= len(ORDERS) / 2:
        log.critical("Half or more of the batch failed (%d/%d), halting the queue", failed, len(ORDERS))

    # NOTSET on a logger means "ask my ancestors". This logger has no level of
    # its own, so getEffectiveLevel() resolves to DEBUG, inherited from "shop".
    quiet = logging.getLogger("shop.audit.trail")
    log.debug(
        "Level of %s is %s, effective level is %s",
        quiet.name,
        logging.getLevelName(quiet.level),
        logging.getLevelName(quiet.getEffectiveLevel()),
    )
    return shipped, failed


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.config.dictConfig(LOGGING_CONFIG)
    run_batch()
    print(f"\nFull log (DEBUG and up) written to: {LOG_FILE}")


if __name__ == "__main__":
    main()
