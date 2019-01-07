import operator
from typing import List
from pint import UnitRegistry

ureg = UnitRegistry()

weights = [{"text": "26g", "value": "26", "unit": "kg"}, {"text": "17g", "value": "17", "unit": "g"}, {"text": "31g", "value": "31", "unit": "mg"}]


class WeightInsight:
    __slots__ = ('text', 'value', 'unit', 'quantity')

    def __init__(self, text: str, value: str, unit: str):
        self.text = text
        self.value = value
        self.unit = self.normalize_unit(unit)
        self.quantity = ureg.Quantity(f"{self.value} * {self.unit}")

    @staticmethod
    def normalize_value(value):
        return value

    @staticmethod
    def normalize_unit(unit):
        return unit.lower()


def select_weights(weight_insights: List[WeightInsight]):
    ranked_weights = sorted(weight_insights,
                            key=operator.attrgetter('quantity'),
                            reverse=True)

    if len(ranked_weights):
        pass


insights = [WeightInsight(**w) for w in weights]

