
def mask_imei(imei):
    """
    Removes dashes and spaces, then hides all but
    the last four characters.
    """

    if imei is None:
        return ""

    if not isinstance(imei, str):
        imei = str(imei)

    imei = imei.replace("-", "").replace(" ", "")

    if not imei:
        return ""

    if len(imei) <= 4:
        return imei

    return "*" * (len(imei) - 4) + imei[-4:]


def parse_parts_order(text):
    """
    Parses 'screen x1; battery x2' into a dictionary.
    Invalid entries are skipped.
    """

    if not isinstance(text, str) or not text.strip():
        return {}

    order = {}

    for item in text.split(";"):
        item = item.strip()

        if not item or "x" not in item:
            continue

        part, qty = item.rsplit("x", 1)

        part = part.strip()
        qty = qty.strip()

        if not part:
            continue

        try:
            quantity = int(qty)
        except ValueError:
            continue

        order[part] = quantity

    return order


def parse_model(text):
    """
    Splits 'Brand Model name' into a (brand, model) tuple.
    Handles empty and invalid inputs.
    """

    if not isinstance(text, str):
        return "", ""

    text = text.strip()

    if not text:
        return "", ""

    parts = text.split(None, 1)

    brand = parts[0].title()
    model = parts[1].strip() if len(parts) == 2 else ""

    return brand, model


def main():

    print("==== Running mask_imei ====")

    value = input(
        "Enter an IMEI number (e.g. 35-209900-176148-1): "
    )

    print("Masked IMEI:", mask_imei(value))

    print("\n==== Running parse_parts_order ====")

    value = input(
        "Enter parts and quantities as PART xQTY "
        "separated by ; (e.g. screen x1; battery x2): "
    )

    print("Parts order:", parse_parts_order(value))

    print("\n==== Running parse_model ====")

    value = input(
        "Enter the phone brand and model "
        "(e.g. Samsung Galaxy S23): "
    )

    print("Brand and model:", parse_model(value))


if __name__ == "__main__":
    main()
