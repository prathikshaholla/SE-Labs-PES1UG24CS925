
from hypothesis import given, strategies as st

from phone_repair_quote_parser import (
    mask_imei,
    parse_parts_order,
    parse_model
)


# Test 1: Fuzz testing mask_imei
@given(st.text() | st.none())
def test_mask_imei_no_crash(s):
    try:
        mask_imei(s)
    except Exception as e:
        assert False, f"mask_imei crashed with: {e}"


# Test 2: Fuzz testing parse_parts_order
@given(st.text() | st.none())
def test_parse_parts_order_no_crash(s):
    try:
        parse_parts_order(s)
    except Exception as e:
        assert False, f"parse_parts_order crashed with: {e}"


# Test 3: Fuzz testing parse_model
@given(st.text() | st.none())
def test_parse_model_no_crash(s):
    try:
        parse_model(s)
    except Exception as e:
        assert False, f"parse_model crashed with: {e}"
