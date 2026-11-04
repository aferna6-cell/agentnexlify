"""Public referral codes are not widget API keys."""

from backend.services.referral import (
    SHARE_LINK_NO_REF,
    is_public_referral_code,
    public_share_link,
    resolve_public_click_ref,
)


def test_null_or_anx_code_falls_back_to_link_without_ref():
    """Pre-202 rows: NULL or a stored widget key must not leak into the link."""
    for raw in (None, "", "   ", "anx_live_widget_key"):
        code, link = public_share_link(raw)
        assert code == ""
        assert link == SHARE_LINK_NO_REF
        assert "ref=" not in link
        assert "anx_" not in link
        assert "anx_" not in code


def test_public_code_is_the_only_ref():
    code, link = public_share_link("ab12cd34")
    assert code == "ab12cd34"
    assert "ref=ab12cd34" in link
    assert "anx_" not in link


def test_widget_key_is_not_public():
    assert is_public_referral_code("anx_live_key") is False
    assert is_public_referral_code("ab12cd34") is True
    assert is_public_referral_code("") is False
    assert is_public_referral_code(None) is False


def test_short_or_punctuated_codes_are_rejected():
    assert is_public_referral_code("abc") is False
    assert is_public_referral_code("ab12-cd") is False


def test_legacy_key_resolves_to_public_code_and_is_not_returned():
    class _Result:
        def __init__(self, data):
            self.data = data

    class _Chain:
        def __init__(self, data):
            self._data = data

        def select(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def limit(self, *_a, **_k):
            return self

        def execute(self):
            return _Result(self._data)

    class _DB:
        def table(self, name):
            if name == "widget_configs":
                return _Chain([{"tenant_id": "ten-1"}])
            if name == "tenants":
                return _Chain([{"referral_code": "ab12cd34"}])
            raise AssertionError(name)

    resolved = resolve_public_click_ref(_DB(), "anx_secret_key_value")
    assert resolved == "ab12cd34"
    assert not resolved.startswith("anx_")


def test_unknown_legacy_key_is_dropped():
    class _Result:
        data = []

    class _Chain:
        def select(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def limit(self, *_a, **_k):
            return self

        def execute(self):
            return _Result()

    class _DB:
        def table(self, _name):
            return _Chain()

    assert resolve_public_click_ref(_DB(), "anx_missing") is None


class _Rows:
    def __init__(self, data=None, error=None):
        self.data = data if data is not None else []
        self.error = error

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        if self.error is not None:
            raise self.error
        return type("Result", (), {"data": self.data})()


class _ClickDB:
    def __init__(self, tenants):
        self.tenants = tenants

    def table(self, name):
        if name == "tenants":
            return self.tenants
        raise AssertionError(name)


def test_click_decision_drops_blank_unknown_and_failed_lookups():
    from backend.services.referral import decide_referral_click

    db = _ClickDB(_Rows())
    assert decide_referral_click(db, None).store_as is None
    assert decide_referral_click(db, "   ").store_as is None
    assert decide_referral_click(db, "not a code").store_as is None
    assert decide_referral_click(db, "ab12cd34").store_as is None

    failed = _ClickDB(_Rows(error=RuntimeError("db down")))
    assert decide_referral_click(failed, "ab12cd34").store_as is None

    found = _ClickDB(_Rows([{"id": "ten-9"}]))
    decision = decide_referral_click(found, "ab12cd34")
    assert decision.store_as == "ab12cd34"
    assert decision.tenant_id == "ten-9"
    assert decision.loud_unrecordable is False


def test_legacy_key_without_public_code_is_not_echoed():
    from backend.services.referral import decide_referral_click, resolve_public_click_ref

    class _DB:
        def table(self, name):
            if name == "widget_configs":
                return _Rows([{"tenant_id": "ten-1"}])
            if name == "tenants":
                return _Rows([{"referral_code": None}])
            raise AssertionError(name)

    decision = decide_referral_click(_DB(), "anx_real_key")
    assert decision.loud_unrecordable is True
    assert decision.store_as == "ten-1"
    assert resolve_public_click_ref(_DB(), "anx_real_key") is None

    class _NoTenantId:
        def table(self, name):
            if name == "widget_configs":
                return _Rows([{"tenant_id": None}])
            raise AssertionError(name)

    assert decide_referral_click(_NoTenantId(), "anx_real_key").store_as is None

    class _Broken:
        def table(self, name):
            if name == "widget_configs":
                return _Rows([{"tenant_id": "ten-1"}])
            if name == "tenants":
                return _Rows(error=RuntimeError("db down"))
            raise AssertionError(name)

    assert decide_referral_click(_Broken(), "anx_real_key").store_as is None


def test_widget_watermark_omits_non_public_codes():
    from backend.routers.widget_config import _public_referral_code

    assert _public_referral_code("anx_secret") is None
    assert _public_referral_code("  ab12cd34  ") == "ab12cd34"
