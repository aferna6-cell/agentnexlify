"""Unit tests for invoice_email_template — pure HTML, no DB."""

from backend.services.invoice_email_template import build_invoice_email_html


def _base_invoice():
    return {
        "invoice_number": "INV-0001",
        "total": 100.0,
        "subtotal": 90.0,
        "tax_amount": 10.0,
        "due_date": "2026-01-01",
        "notes": "",
        "stripe_payment_link": "",
        "items_json": [{"description": "Service", "quantity": 1, "unit_price": 90.0}],
    }


def test_includes_invoice_number_and_total():
    html = build_invoice_email_html(_base_invoice(), {"business_name": "Biz"}, {"name": "Cust"})
    assert "INV-0001" in html
    assert "$100.00" in html
    assert "Biz" in html
    assert "Cust" in html


def test_escapes_customer_name():
    html = build_invoice_email_html(_base_invoice(), {}, {"name": "<script>alert(1)</script>"})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_pay_button_only_when_link_present():
    no_link = _base_invoice()
    html_no = build_invoice_email_html(no_link, {}, {})
    assert "Pay Now" not in html_no

    with_link = _base_invoice()
    with_link["stripe_payment_link"] = "https://buy.stripe.com/xyz"
    html_yes = build_invoice_email_html(with_link, {}, {})
    assert "Pay Now" in html_yes
    assert "https://buy.stripe.com/xyz" in html_yes


def test_tax_row_hidden_when_zero():
    inv = _base_invoice()
    inv["tax_amount"] = 0
    html = build_invoice_email_html(inv, {}, {})
    assert ">Tax<" not in html


def test_default_customer_name_when_missing():
    html = build_invoice_email_html(_base_invoice(), {}, {})
    assert "Valued Customer" in html
