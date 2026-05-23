"""Tests for backend/services/form_rendering.py — pure logic, no DB."""

import re


from backend.services.form_rendering import (
    extract_lead_fields,
    generate_public_token,
    render_form_embed_html,
    validate_required_fields,
)


# ---------------------------------------------------------------------------
# generate_public_token
# ---------------------------------------------------------------------------

class TestGeneratePublicToken:
    def test_token_has_frm_prefix(self):
        token = generate_public_token()
        assert token.startswith("frm_")

    def test_token_is_url_safe(self):
        token = generate_public_token()
        # URL-safe base64 alphabet
        assert re.fullmatch(r"frm_[A-Za-z0-9_\-]+", token)

    def test_token_uniqueness(self):
        tokens = {generate_public_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_token_has_sufficient_entropy(self):
        # secrets.token_urlsafe(24) → 32 base64url chars
        token = generate_public_token()
        body = token[len("frm_") :]
        assert len(body) >= 30


# ---------------------------------------------------------------------------
# validate_required_fields
# ---------------------------------------------------------------------------

class TestValidateRequiredFields:
    def test_no_fields_returns_empty(self):
        assert validate_required_fields([], {}) == []

    def test_none_fields_returns_empty(self):
        assert validate_required_fields(None, {}) == []  # type: ignore[arg-type]

    def test_missing_required_returns_label(self):
        fields = [{"id": "email", "label": "Email", "required": True}]
        missing = validate_required_fields(fields, {})
        assert missing == ["Email"]

    def test_blank_string_treated_as_missing(self):
        fields = [{"id": "email", "label": "Email", "required": True}]
        missing = validate_required_fields(fields, {"email": "   "})
        assert missing == ["Email"]

    def test_present_value_not_missing(self):
        fields = [{"id": "email", "label": "Email", "required": True}]
        missing = validate_required_fields(fields, {"email": "user@example.com"})
        assert missing == []

    def test_optional_field_missing_not_reported(self):
        fields = [{"id": "company", "label": "Company", "required": False}]
        missing = validate_required_fields(fields, {})
        assert missing == []

    def test_falls_back_to_id_when_label_missing(self):
        fields = [{"id": "email_addr", "required": True}]
        missing = validate_required_fields(fields, {})
        assert missing == ["email_addr"]

    def test_multiple_missing_collected_in_order(self):
        fields = [
            {"id": "name", "label": "Name", "required": True},
            {"id": "email", "label": "Email", "required": True},
            {"id": "phone", "label": "Phone", "required": False},
        ]
        missing = validate_required_fields(fields, {"phone": "5551234"})
        assert missing == ["Name", "Email"]

    def test_non_string_value_accepted(self):
        # Numbers, bools etc. pass the "present" check
        fields = [{"id": "age", "label": "Age", "required": True}]
        missing = validate_required_fields(fields, {"age": 0})
        assert missing == []


# ---------------------------------------------------------------------------
# extract_lead_fields
# ---------------------------------------------------------------------------

class TestExtractLeadFields:
    def test_empty_submission_returns_all_none(self):
        result = extract_lead_fields({}, [])
        assert result == {"name": None, "email": None, "phone": None}

    def test_extracts_by_field_type_email(self):
        fields = [{"id": "contact_box", "type": "email"}]
        result = extract_lead_fields({"contact_box": "a@b.com"}, fields)
        assert result["email"] == "a@b.com"

    def test_extracts_by_field_type_phone(self):
        fields = [{"id": "callback", "type": "phone"}]
        result = extract_lead_fields({"callback": "5551234567"}, fields)
        assert result["phone"] == "5551234567"

    def test_extracts_by_id_heuristic_name(self):
        result = extract_lead_fields(
            {"full_name": "Jane Doe"},
            [{"id": "full_name", "type": "text"}],
        )
        assert result["name"] == "Jane Doe"

    def test_extracts_by_id_heuristic_email(self):
        result = extract_lead_fields(
            {"email": "x@y.com"},
            [{"id": "email", "type": "text"}],
        )
        assert result["email"] == "x@y.com"

    def test_extracts_by_id_heuristic_phone_synonyms(self):
        for alias in ("phone", "phone_number", "mobile", "tel"):
            result = extract_lead_fields(
                {alias: "5551111"},
                [{"id": alias, "type": "text"}],
            )
            assert result["phone"] == "5551111", f"alias {alias} failed"

    def test_strips_whitespace(self):
        result = extract_lead_fields(
            {"email": "  x@y.com  "},
            [{"id": "email", "type": "email"}],
        )
        assert result["email"] == "x@y.com"

    def test_blank_value_skipped(self):
        result = extract_lead_fields(
            {"email": "   "},
            [{"id": "email", "type": "email"}],
        )
        assert result["email"] is None

    def test_non_string_value_skipped(self):
        result = extract_lead_fields(
            {"age": 30},
            [{"id": "age", "type": "number"}],
        )
        assert result["name"] is None
        assert result["email"] is None
        assert result["phone"] is None

    def test_unknown_id_not_extracted_as_name(self):
        result = extract_lead_fields(
            {"favorite_color": "blue"},
            [{"id": "favorite_color", "type": "text"}],
        )
        assert result["name"] is None

    def test_all_three_fields_extracted_together(self):
        fields = [
            {"id": "your_name", "type": "text"},
            {"id": "email", "type": "email"},
            {"id": "phone", "type": "phone"},
        ]
        data = {
            "your_name": "Jane",
            "email": "jane@example.com",
            "phone": "5551234",
        }
        result = extract_lead_fields(data, fields)
        assert result == {
            "name": "Jane",
            "email": "jane@example.com",
            "phone": "5551234",
        }

    def test_none_inputs_safe(self):
        result = extract_lead_fields(None, None)  # type: ignore[arg-type]
        assert result == {"name": None, "email": None, "phone": None}


# ---------------------------------------------------------------------------
# render_form_embed_html
# ---------------------------------------------------------------------------

class TestRenderFormEmbedHtml:
    def _form(self, **overrides):
        base = {
            "name": "Contact Us",
            "description": "Get in touch",
            "fields_json": [],
            "settings_json": {},
            "success_message": "Thanks!",
        }
        base.update(overrides)
        return base

    def test_returns_full_html_document(self):
        html_out = render_form_embed_html(self._form())
        assert html_out.startswith("<!DOCTYPE html>")
        assert "</html>" in html_out

    def test_form_name_appears_in_title_and_heading(self):
        html_out = render_form_embed_html(self._form(name="My Form"))
        assert "<title>My Form</title>" in html_out
        assert "<h1>My Form</h1>" in html_out

    def test_description_rendered_when_present(self):
        html_out = render_form_embed_html(self._form(description="Tell us"))
        assert "class='desc'" in html_out
        assert "Tell us" in html_out

    def test_description_omitted_when_blank(self):
        html_out = render_form_embed_html(self._form(description=""))
        assert "class='desc'" not in html_out

    def test_escapes_form_name(self):
        html_out = render_form_embed_html(self._form(name="<script>alert(1)</script>"))
        assert "<script>alert(1)</script>" not in html_out
        assert "&lt;script&gt;" in html_out

    def test_escapes_description(self):
        html_out = render_form_embed_html(self._form(description="<img src=x>"))
        assert "<img src=x>" not in html_out
        assert "&lt;img" in html_out

    def test_default_theme_color_used(self):
        html_out = render_form_embed_html(self._form())
        assert "#7c3aed" in html_out

    def test_custom_theme_color_used(self):
        html_out = render_form_embed_html(
            self._form(settings_json={"theme_color": "#ff0000"})
        )
        assert "#ff0000" in html_out

    def test_custom_submit_button_text(self):
        html_out = render_form_embed_html(
            self._form(settings_json={"submit_button_text": "Send Now"})
        )
        assert ">Send Now</button>" in html_out

    def test_success_message_in_script(self):
        html_out = render_form_embed_html(self._form(success_message="You rock!"))
        assert "You rock!" in html_out

    def test_renders_text_field(self):
        fields = [{"id": "name", "label": "Full Name", "type": "text", "required": True}]
        html_out = render_form_embed_html(self._form(fields_json=fields))
        assert 'type="text"' in html_out
        assert 'name="name"' in html_out
        assert "Full Name" in html_out
        assert "required" in html_out

    def test_renders_email_field(self):
        fields = [{"id": "email", "label": "Email", "type": "email"}]
        html_out = render_form_embed_html(self._form(fields_json=fields))
        assert 'type="email"' in html_out

    def test_renders_phone_field_as_tel_input(self):
        fields = [{"id": "phone", "label": "Phone", "type": "phone"}]
        html_out = render_form_embed_html(self._form(fields_json=fields))
        assert 'type="tel"' in html_out

    def test_renders_textarea(self):
        fields = [{"id": "msg", "label": "Message", "type": "textarea"}]
        html_out = render_form_embed_html(self._form(fields_json=fields))
        assert "<textarea" in html_out
        assert 'name="msg"' in html_out

    def test_renders_select_with_options(self):
        fields = [
            {"id": "size", "label": "Size", "type": "select", "options": ["S", "M", "L"]}
        ]
        html_out = render_form_embed_html(self._form(fields_json=fields))
        assert "<select" in html_out
        assert "<option value=\"S\">S</option>" in html_out
        assert "<option value=\"M\">M</option>" in html_out

    def test_renders_radio_group(self):
        fields = [
            {"id": "color", "label": "Color", "type": "radio", "options": ["Red", "Blue"]}
        ]
        html_out = render_form_embed_html(self._form(fields_json=fields))
        assert 'type="radio"' in html_out
        assert 'value="Red"' in html_out
        assert 'value="Blue"' in html_out

    def test_renders_checkbox(self):
        fields = [{"id": "agree", "label": "I agree", "type": "checkbox"}]
        html_out = render_form_embed_html(self._form(fields_json=fields))
        assert 'type="checkbox"' in html_out
        assert 'name="agree"' in html_out

    def test_unknown_field_type_skipped(self):
        fields = [
            {"id": "good", "label": "Good", "type": "text"},
            {"id": "bad", "label": "Bad", "type": "alien"},
        ]
        html_out = render_form_embed_html(self._form(fields_json=fields))
        assert 'name="good"' in html_out
        assert 'name="bad"' not in html_out

    def test_required_marker_shown_for_required_fields(self):
        fields = [{"id": "x", "label": "X", "type": "text", "required": True}]
        html_out = render_form_embed_html(self._form(fields_json=fields))
        assert "*" in html_out

    def test_escapes_field_options(self):
        fields = [
            {"id": "x", "label": "X", "type": "select", "options": ["<bad>"]}
        ]
        html_out = render_form_embed_html(self._form(fields_json=fields))
        assert "<bad>" not in html_out
        assert "&lt;bad&gt;" in html_out

    def test_default_success_message_when_none(self):
        html_out = render_form_embed_html(self._form(success_message=None))
        assert "Thank you for your submission!" in html_out

    def test_powered_by_attribution_present(self):
        html_out = render_form_embed_html(self._form())
        assert "AgentNexLiFy" in html_out
