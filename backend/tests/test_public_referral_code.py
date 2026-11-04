"""Public referral codes are not widget API keys."""

from backend.services.referral import is_public_referral_code, resolve_public_click_ref


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
