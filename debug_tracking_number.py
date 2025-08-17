#!/usr/bin/env python3
import argparse
import pprint

from tracking_numbers.definition import TrackingNumberDefinition
from tracking_numbers.helpers.spec import iter_courier_specs
from tracking_numbers.types import Courier


def main():
    parser = argparse.ArgumentParser(description="Debug tracking number parser.")
    parser.add_argument("tracking_number", help="Tracking number to debug")
    args = parser.parse_args()

    tracking_number = args.tracking_number
    found = False

    for spec in iter_courier_specs():
        courier = Courier(
            name=spec["name"],
            code=spec["courier_code"],
        )
        for tn_spec in spec["tracking_numbers"]:
            definition = TrackingNumberDefinition.from_spec(courier, tn_spec)
            result = definition.test(tracking_number)
            if result:
                found = True
                print(f"Courier: {courier.name} ({courier.code})")
                print("Result:")
                pprint.pprint(result.__dict__)

                # Are any of the validation errors related to the checksum?
                checksum_errors = [
                    message
                    for (error, message) in result.validation_errors
                    if error == "checksum"
                ]
                if checksum_errors:
                    print(f"Checksum errors found: {checksum_errors}")
                    if definition.checksum_validator:
                        print(
                            f"Expected check digit: {definition.checksum_validator._check_digit(result.serial_number)}",
                        )

    if not found:
        print("No matching courier definition found for this tracking number.")


if __name__ == "__main__":
    main()
