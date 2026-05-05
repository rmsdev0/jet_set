from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def cents_to_dollars(cents: int) -> Decimal:
    return (Decimal(cents) / Decimal("100")).quantize(Decimal("0.01"))


def dollars_to_cents(dollars: str | float | Decimal) -> int:
    return int((Decimal(str(dollars)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def percentage_amount(total_cents: int, percentage: float) -> int:
    return int((Decimal(total_cents) * Decimal(str(percentage))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
