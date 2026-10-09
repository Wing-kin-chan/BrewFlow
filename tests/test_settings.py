from brewflow.settings import load_queue_settings


def test_queue_validation_values_come_from_static_config():
    settings = load_queue_settings()

    assert "Latte" in settings.drinks
    assert settings.milks == ("Whole", "Semi-skimmed", "Oat", "Soy")
    assert settings.textures == ("Extra Wet", "Wet", "Dry", "Extra Dry")
    assert settings.search_depth == 1
    assert settings.max_batch_volume == 5
