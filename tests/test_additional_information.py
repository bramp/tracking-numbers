import json
import os

from tracking_numbers.definition import TrackingNumberDefinition
from tracking_numbers.types import Courier

# Load the S10 tracking number spec from the JSON file
spec_path = os.path.join(os.path.dirname(__file__), "fixtures/example_s10.json")
with open(spec_path) as f:
    tn_spec = json.load(f)

courier = Courier(
    name="S10 International Standard",
    code="s10",
)

definition = TrackingNumberDefinition.from_spec(courier, tn_spec)


def test_s10_additional_info():
    # Test case for extracting additional information from the tracking number
    tracking = definition.test("RB123456785GB")

    assert tracking is not None
    assert tracking.courier_info == {
        "code": "s10",
        "name": "Royal Mail Group plc",
        "url": "http://www.royalmail.com/postcode-finder?gear=postcode&campaignid=postcodefinder_redirect",
        "upu_reference_url": "http://www.upu.int/en/the-upu/member-countries/western-europe/great-britain.html",
        "country": "Great Britain",
    }

    assert tracking.service_type == {
        "code": "RB",
        "name": "Letter Post Registered",
        "description": "Prepaid first-class mail.",
    }

    assert tracking.valid


def test_s10_missing_additional_info():
    print(definition)

    tracking = definition.test("AB123456785NP")
    assert tracking is not None

    # AB is a unknown courier code, so we default back to s10
    assert tracking.courier_info == {
        "code": "s10",
        "name": "S10 International Standard",
    }

    assert tracking.service_type == {
        "code": "AB",
    }

    assert not tracking.valid
    assert tracking.validation_errors == [
        (
            "Courier",
            "Courier not found in additional information",
        ),
    ]
