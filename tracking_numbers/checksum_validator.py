from abc import ABCMeta
from abc import abstractmethod
from typing import List
from typing import Optional

from tracking_numbers.helpers.repr import repr_with_args
from tracking_numbers.types import SerialNumber
from tracking_numbers.types import Spec
from tracking_numbers.types import to_int


class ChecksumValidator(metaclass=ABCMeta):
    def __repr__(self):
        return repr_with_args(self)

    @abstractmethod
    def passes(self, serial_number: SerialNumber, check_digit: str) -> bool:
        raise NotImplementedError

    @classmethod
    def from_spec(cls, validation_spec: Spec) -> Optional["ChecksumValidator"]:
        checksum_spec = validation_spec.get("checksum")
        if not checksum_spec:
            return None

        strategy = checksum_spec.get("name")
        if strategy == "s10":
            return S10()

        elif strategy == "mod7":
            return Mod7()

        elif strategy == "mod10":
            return Mod10(
                odds_multiplier=checksum_spec.get("odds_multiplier"),
                evens_multiplier=checksum_spec.get("evens_multiplier"),
            )

        elif strategy == "mod_37_36":
            return Mod_37_36()

        elif strategy == "sum_product_with_weightings_and_modulo":
            return SumProductWithWeightsAndModulo(
                weights=checksum_spec["weightings"],
                first_modulo=checksum_spec["modulo1"],
                second_modulo=checksum_spec["modulo2"],
            )

        elif strategy == "luhn":
            return Luhn()

        raise ValueError(f"Unknown checksum: {strategy}")


class S10(ChecksumValidator):
    WEIGHTS = [8, 6, 4, 2, 3, 5, 9, 7]

    def passes(self, serial_number: SerialNumber, check_digit: str) -> bool:
        total = 0
        for digit, weight in zip(serial_number, self.WEIGHTS):
            total += int(digit) * weight

        remainder = total % 11
        if remainder == 1:
            check = 0
        elif remainder == 0:
            check = 5
        else:
            check = 11 - remainder

        return check == int(check_digit)


class Mod10(ChecksumValidator):
    def __init__(
        self,
        odds_multiplier: Optional[int] = None,
        evens_multiplier: Optional[int] = None,
    ):
        self.odds_multiplier = odds_multiplier
        self.evens_multiplier = evens_multiplier

    def __repr__(self):
        return repr_with_args(
            self,
            odds_multiplier=self.odds_multiplier,
            evens_multiplier=self.evens_multiplier,
        )

    def passes(self, serial_number: SerialNumber, check_digit: str) -> bool:
        total = 0
        for index, digit in enumerate(serial_number):
            is_even_index = index % 2 == 0
            is_odd_index = not is_even_index

            if is_odd_index and self.odds_multiplier:
                total += int(digit) * self.odds_multiplier
            elif is_even_index and self.evens_multiplier:
                total += int(digit) * self.evens_multiplier
            else:
                total += int(digit)

        check = total % 10
        if check != 0:
            check = 10 - check

        return check == int(check_digit)


class Mod7(ChecksumValidator):
    def passes(self, serial_number: SerialNumber, check_digit: str) -> bool:
        return int(check_digit) == (to_int(serial_number) % 7)


class Mod_37_36(ChecksumValidator):
    WEIGHTS = {chr(i): i + 10 for i in range(26)}  # A=10, B=11, ..., Z=35

    def passes(self, serial_number: SerialNumber, check_digit: str) -> bool:
        # From https://esolutions.dpd.com/dokumente/DPD_Parcel_Label_Specification_2.4.1_EN.pdf
        mod = 36
        cd = mod
        for char in serial_number:
            if char.isalpha():
                val = self.WEIGHTS[char.upper()]
            else:
                val = int(char)
            cd = val + cd
            if cd > mod:
                cd = cd - mod
            cd = cd * 2
            if cd > mod:
                cd = cd - (mod + 1)
        cd = (mod + 1) - cd
        if cd == mod:
            cd = 0
        if cd >= 10:
            # Find the letter corresponding to the value
            computed = next((a for a, val in self.WEIGHTS.items() if val == cd), None)
            if computed is not None:
                computed = computed
            else:
                computed = str(cd)
        else:
            computed = str(cd)
        return str(computed) == check_digit


class SumProductWithWeightsAndModulo(ChecksumValidator):
    def __init__(self, weights: List[int], first_modulo: int, second_modulo: int):
        self.weights = weights
        self.first_modulo = first_modulo
        self.second_modulo = second_modulo

    def __repr__(self):
        return repr_with_args(
            self,
            weights=self.weights,
            first_modulo=self.first_modulo,
            second_modulo=self.second_modulo,
        )

    def passes(self, serial_number: SerialNumber, check_digit: str) -> bool:
        total = 0
        for digit, weight in zip(serial_number, self.weights):
            total += int(digit) * weight

        check = total % self.first_modulo % self.second_modulo
        return check == int(check_digit)


class Luhn(ChecksumValidator):
    """Luhn algorithm for validating a checksum digit.

    See https://en.wikipedia.org/wiki/Luhn_algorithm
    """

    def passes(self, serial_number: SerialNumber, check_digit: str) -> bool:
        total = 0
        digits = list(serial_number)[::-1]
        for i, c in enumerate(digits):
            x = int(c)
            if i % 2 == 0:
                x *= 2
            if x > 9:
                x -= 9
            total += x
        check = total % 10
        if check != 0:
            check = 10 - check
        return check == int(check_digit)
