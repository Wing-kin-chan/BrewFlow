import pytest

from brewflow.settings import (
    load_catalog_settings,
    load_payment_settings,
    load_queue_settings,
)


def test_queue_validation_values_come_from_static_config():
    settings = load_queue_settings()

    assert "Latte" in settings.drinks
    assert settings.milks == ("Whole", "Semi-skimmed", "Oat", "Soy")
    assert settings.textures == ("Extra Wet", "Wet", "Dry", "Extra Dry")
    assert settings.search_depth == 1
    assert settings.max_batch_volume == 5


def test_catalog_uses_gbp_and_complete_nonnegative_milk_pricing():
    catalog = load_catalog_settings()

    assert catalog.currency == "gbp"
    assert catalog.milk_surcharges_minor == {
        "No Milk": 0,
        "Whole": 0,
        "Semi-skimmed": 0,
        "Oat": 60,
        "Soy": 60,
    }


def test_checkout_return_url_must_be_an_absolute_http_url(monkeypatch):
    monkeypatch.setenv("BREWFLOW_CHECKOUT_RETURN_BASE_URL", "javascript:alert(1)")
    with pytest.raises(ValueError, match="absolute HTTP"):
        load_payment_settings()

    monkeypatch.setenv(
        "BREWFLOW_CHECKOUT_RETURN_BASE_URL", "https://payments.example.test/"
    )
    assert (
        load_payment_settings().checkout_return_base_url
        == "https://payments.example.test"
    )


def test_demo_mode_gate_is_disabled_by_default_and_requires_explicit_true(monkeypatch):
    monkeypatch.delenv("BREWFLOW_ALLOW_DEMO_MODE", raising=False)
    assert load_payment_settings().allow_demo_mode is False

    monkeypatch.setenv("BREWFLOW_ALLOW_DEMO_MODE", "true")
    assert load_payment_settings().allow_demo_mode is True

    monkeypatch.setenv("BREWFLOW_ALLOW_DEMO_MODE", "not-true")
    assert load_payment_settings().allow_demo_mode is False
