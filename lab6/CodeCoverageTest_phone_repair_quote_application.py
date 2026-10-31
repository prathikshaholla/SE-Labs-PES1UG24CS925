import pytest
from phone_repair_quote import repair_quote, repair_days, trade_in_value


@pytest.mark.parametrize(
    "part, brand_tier, under_warranty, express, expected",
    [
        ("screen", "budget", False, False, 4600),
        ("battery", "budget", False, False, 1800),
        ("camera", "flagship", False, True, 5800),
        ("charging_port", "flagship", True, False, 300),
        ("battery", "budget", True, True, 800),
        ("screen", "flagship", True, True, 9100),
    ],
)
def test_repair_quote_valid_inputs(part, brand_tier, under_warranty, express, expected):
    assert repair_quote(part, brand_tier, under_warranty, express) == expected


@pytest.mark.parametrize(
    "part, brand_tier, under_warranty, express",
    [
        ("unknown_part", "budget", False, False),
        ("battery", "premium", False, False),
    ],
)
def test_repair_quote_invalid_inputs(part, brand_tier, under_warranty, express):
    with pytest.raises(ValueError):
        repair_quote(part, brand_tier, under_warranty, express)


@pytest.mark.parametrize(
    "part, parts_in_stock, technicians_free, expected",
    [
        ("battery", True, 2, 1),
        ("screen", False, 0, 8),
        ("camera", False, 1, 6),
        ("battery", False, 0, 5),
        ("screen", True, 0, 3),
    ],
)
def test_repair_days(part, parts_in_stock, technicians_free, expected):
    assert repair_days(part, parts_in_stock, technicians_free) == expected


@pytest.mark.parametrize(
    "original_price, age_months, screen_cracked, expected",
    [
        (10000, 6, False, 6000),
        (10000, 12, True, 3000),
        (10000, 13, False, 4000),
        (10000, 24, True, 2000),
        (10000, 25, False, 2000),
        (10000, 48, True, 1000),
        (10000, 49, False, 0),
    ],
)
def test_trade_in_valid_inputs(original_price, age_months, screen_cracked, expected):
    assert trade_in_value(original_price, age_months, screen_cracked) == expected


@pytest.mark.parametrize(
    "original_price, age_months, screen_cracked",
    [
        (0, 0, False),
        (10000, -1, False),
    ],
)
def test_trade_in_invalid_inputs(original_price, age_months, screen_cracked):
    with pytest.raises(ValueError):
        trade_in_value(original_price, age_months, screen_cracked)
