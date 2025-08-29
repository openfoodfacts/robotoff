import functools
import math

import pint


@functools.cache
def get_unit_registry():
    # We initialize UnitRegistry here to prevent
    return pint.UnitRegistry()


def normalize_weight(value: str, unit: str) -> tuple[float, str]:
    """Normalize a weight (product weight or nutrient quantity) by converting the value
    to g for mass and mL for volumes.

    This function returns a (value, unit) tuple, where value is the normalized
    value as a float and unit either 'g' or 'ml'.

    :param value: The numeric part of the weight (e.g. "250" or "1.5")
    :param unit: The unit part of the weight (e.g. "g", "kg", "ml", "l", "oz", "fl oz")
    :raises ValueError: If the unit is unknown or cannot be converted to g or ml
    :return: A tuple of the normalized value and unit
    """
    if "," in value:
        # pint does not recognize ',' separator
        value = value.replace(",", ".")

    if unit == "fl oz":
        # For nutrition labeling, a fluid ounce is equal to 30 ml
        value = str(float(value) * 30)
        unit = "ml"

    ureg = get_unit_registry()
    quantity = ureg.parse_expression(f"{value} {unit}")

    if ureg.gram in quantity.compatible_units():
        normalized_quantity = quantity.to(ureg.gram)
        normalized_unit = "g"
    elif ureg.liter in quantity.compatible_units():
        normalized_quantity = quantity.to(ureg.milliliter)
        normalized_unit = "ml"
    else:
        raise ValueError(f"unknown unit: {quantity.u}")

    # Rounding errors due to float may occur with Pint,
    # round normalized value to floor if there is no significant difference
    normalized_value = normalized_quantity.magnitude
    if math.isclose(math.floor(normalized_value), normalized_value):
        normalized_value = math.floor(normalized_value)

    return normalized_value, normalized_unit
