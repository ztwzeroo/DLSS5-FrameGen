def test_package_importable_with_version():
    import dlss_combo
    assert dlss_combo.__version__ == "0.1.0"
