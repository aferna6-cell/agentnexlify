"""Pure invoice math: subtotal, tax, total computation from line items."""


def compute_invoice_totals(items: list[dict], tax_rate: float) -> tuple[float, float, float]:
    """Return (subtotal, tax_amount, total) from line items and a tax_rate percentage."""
    subtotal = round(sum(
        item.get("quantity", 1) * item.get("unit_price", 0)
        for item in items
    ), 2)
    tax_amount = round(subtotal * (tax_rate / 100), 2)
    total = round(subtotal + tax_amount, 2)
    return subtotal, tax_amount, total
