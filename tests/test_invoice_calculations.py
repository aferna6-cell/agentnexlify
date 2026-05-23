"""Unit tests for invoice_calculations — pure math, no DB."""

from backend.services.invoice_calculations import compute_invoice_totals


def test_empty_items_returns_zero_totals():
    subtotal, tax, total = compute_invoice_totals([], tax_rate=8.25)
    assert subtotal == 0
    assert tax == 0
    assert total == 0


def test_single_item_no_tax():
    items = [{"description": "x", "quantity": 2, "unit_price": 10.0}]
    subtotal, tax, total = compute_invoice_totals(items, tax_rate=0.0)
    assert subtotal == 20.0
    assert tax == 0.0
    assert total == 20.0


def test_multi_item_with_tax():
    items = [
        {"quantity": 1, "unit_price": 100.0},
        {"quantity": 2, "unit_price": 50.0},
    ]
    subtotal, tax, total = compute_invoice_totals(items, tax_rate=10.0)
    assert subtotal == 200.0
    assert tax == 20.0
    assert total == 220.0


def test_missing_quantity_defaults_to_one():
    items = [{"unit_price": 42.0}]
    subtotal, _, _ = compute_invoice_totals(items, tax_rate=0.0)
    assert subtotal == 42.0


def test_missing_unit_price_defaults_to_zero():
    items = [{"quantity": 5}]
    subtotal, _, total = compute_invoice_totals(items, tax_rate=10.0)
    assert subtotal == 0.0
    assert total == 0.0


def test_rounding_to_two_decimals():
    items = [{"quantity": 3, "unit_price": 10.005}]
    subtotal, _, _ = compute_invoice_totals(items, tax_rate=0.0)
    assert subtotal == round(30.015, 2)
