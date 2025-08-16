from typing import Dict

import pytest

from tracking_numbers.checksum_validator import Luhn
from tracking_numbers.checksum_validator import Mod10
from tracking_numbers.checksum_validator import Mod7
from tracking_numbers.checksum_validator import Mod_37_36
from tracking_numbers.checksum_validator import S10
from tracking_numbers.checksum_validator import SumProductWithWeightsAndModulo
from tracking_numbers.serial_number import DefaultSerialNumberParser


serials_and_checks = [
    (
        "12345678",
        {
            "S10": "5",
            "Mod10": "4",
            "Mod7": "2",
            "Mod_37_36": "W",
            "Luhn": "2",
            "SumProduct": "4",
        },
    ),
    (
        "45678",
        {
            "S10": 8,
            "Mod10": "0",
            "Mod7": "3",
            "Mod_37_36": "V",
            "Luhn": "0",
            "SumProduct": "2",
        },
    ),
    (
        "00007",
        {
            "S10": 1,
            "Mod10": "3",
            "Mod7": "0",
            "Mod_37_36": "I",
            "Luhn": "5",
            "SumProduct": "0",
        },
    ),
    (
        "A12345",
        {
            "Mod_37_36": "J",
        },
    ),
]

algorithms = {
    "S10": S10(),
    "Mod10": Mod10(),
    "Mod7": Mod7(),
    "Mod_37_36": Mod_37_36(),
    "Luhn": Luhn(),
    "SumProduct": SumProductWithWeightsAndModulo([1, 2, 3], 10, 5),
}

parser = DefaultSerialNumberParser()


@pytest.mark.parametrize("serial, checks", serials_and_checks)
@pytest.mark.parametrize("algo_name", algorithms.keys())
def test_valid_checksum(algo_name, serial: str, checks: Dict[str, str]):
    validator = algorithms[algo_name]
    parsed_serial = parser.parse(serial)

    if algo_name not in checks:
        try:
            validator._check_digit(parsed_serial)

            assert False, (
                f"Expected {algo_name} to fail for {serial} "
                f"instead it provided check_digit '{validator._check_digit(parsed_serial)}'"
            )

        except ValueError:
            pass

    else:
        check_digit = checks[algo_name]
        assert validator.passes(
            parsed_serial,
            check_digit,
        ), (
            f"Expected {algo_name} to pass for {serial} with check_digit {check_digit} "
            f"instead it provided check_digit '{validator._check_digit(parsed_serial)}'"
        )


def test_valid_Mod_37_36_checksum():
    # A few extra test cases for Mod_37_36 from
    # https://esolutions.dpd.com/dokumente/DPD_Parcel_Label_Specification_2.4.1_EN.pdf
    test_cases = [
        ("123AB", "X"),
        ("ABC987", "E"),
    ]

    validator = algorithms["Mod_37_36"]
    for serial, expected in test_cases:
        parsed_serial = parser.parse(serial)
        assert validator.passes(
            parsed_serial,
            expected,
        ), (
            f"Expected Mod_37_36 to pass for {serial} with check_digit {expected} "
            f"instead it provided check_digit '{validator._check_digit(parsed_serial)}'"
        )


def test_valid_Luhn_checksum():
    # A few extra test cases for Luhn from
    # https://en.wikipedia.org/wiki/Luhn_algorithm
    test_cases = [
        ("1789372997", "4"),
    ]

    validator = algorithms["Luhn"]
    for serial, expected in test_cases:
        parsed_serial = parser.parse(serial)
        assert validator.passes(
            parsed_serial,
            expected,
        ), (
            f"Expected Luhn to pass for {serial} with check_digit {expected} "
            f"instead it provided check_digit '{validator._check_digit(parsed_serial)}'"
        )
