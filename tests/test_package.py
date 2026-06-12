import qq_ai_bot


def test_package_exposes_version() -> None:
    assert isinstance(qq_ai_bot.__version__, str)
    assert qq_ai_bot.__version__
