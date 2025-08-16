import os
from typing import List
from typing import Optional

from tracking_numbers.definition import TrackingNumberDefinition
from tracking_numbers.types import TrackingNumber

if not os.environ.get("CODE_GENERATING"):
    from tracking_numbers._generated import DEFINITIONS
else:
    # When running codegen, it's very possible that the items in
    # DEFINITIONS are out of date / can't be successfully constructed
    # so we use an empty list so that codegen can still import utils
    DEFINITIONS = []


def get_tracking_number(number: str, validate=True) -> Optional[TrackingNumber]:
    """Returns a TrackingNumber that matches the given number.

    Args:
        number (str): The tracking number to match.
        validate (bool, optional): Whether to validate the tracking number (e.g
        checksum and other rules). Defaults to True.

    Returns:
        Optional[TrackingNumber]: The matching TrackingNumber, or None if no match is found.
    """
    for tn_definition in DEFINITIONS:
        tracking_number = tn_definition.test(number)
        if tracking_number and (not validate or tracking_number.valid):
            return tracking_number

    return None


def possible_tracking_number(number: str) -> List[TrackingNumber]:
    """Returns a list of TrackingNumbers that match the given number."""
    possible_numbers = []
    for tn_definition in DEFINITIONS:
        tracking_number = tn_definition.test(number)
        if tracking_number:
            possible_numbers.append(tracking_number)

    return possible_numbers


def get_definition(product_name: str) -> Optional[TrackingNumberDefinition]:
    for tn_definition in DEFINITIONS:
        if tn_definition.product.name.lower() == product_name.lower():
            return tn_definition

    return None
