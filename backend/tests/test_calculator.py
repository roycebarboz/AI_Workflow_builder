from app.tools.calculator import calculator


def test_basic_arithmetic():
    assert calculator("2 + 2") == "4"
    assert calculator("(2 + 3) * 4") == "20"
    assert calculator("2 ** 10") == "1024"


def test_division_by_zero_does_not_raise():
    result = calculator("1 / 0")
    assert result.startswith("Error:")


def test_rejects_non_arithmetic_input():
    result = calculator("__import__('os').system('echo pwned')")
    assert result.startswith("Error:")
