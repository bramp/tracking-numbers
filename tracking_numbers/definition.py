from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Optional
from typing import Pattern
from typing import Tuple

from tracking_numbers.checksum_validator import ChecksumValidator
from tracking_numbers.compat import parse_regex
from tracking_numbers.helpers.repr import repr_with_args
from tracking_numbers.serial_number import DefaultSerialNumberParser
from tracking_numbers.serial_number import SerialNumberParser
from tracking_numbers.serial_number import UPSSerialNumberParser
from tracking_numbers.types import Courier
from tracking_numbers.types import Info
from tracking_numbers.types import Product
from tracking_numbers.types import SerialNumber
from tracking_numbers.types import Spec
from tracking_numbers.types import TrackingNumber
from tracking_numbers.types import ValidationError
from tracking_numbers.value_matcher import ValueMatcher

MatchData = Dict[str, str]


@dataclass
class Additional:
    """Spec for extracting additional information from the tracking number."""

    name: str
    regex_group_name: str
    value_matchers: List[Tuple[ValueMatcher, Info]]

    @classmethod
    def from_spec(cls, spec: Spec) -> "Additional":
        value_matchers: List[Tuple[ValueMatcher, Info]] = []
        for value_matcher_spec in spec["lookup"]:
            # Create a copy of the value_matcher_spec without the 'match' and 'matches_regex' keys
            info = {
                k: value_matcher_spec[k]
                for k in set(list(value_matcher_spec.keys()))
                - {"matches", "matches_regex"}
            }

            value_matchers.append((ValueMatcher.from_spec(value_matcher_spec), info))

        return Additional(
            name=spec["name"],
            regex_group_name=spec["regex_group_name"],
            value_matchers=value_matchers,
        )


@dataclass
class AdditionalValidator:
    """Spec for validating additional information extracted from the tracking number."""

    exists: List[str]

    @classmethod
    def from_spec(cls, spec: Spec) -> Optional["AdditionalValidator"]:
        if spec is None or "exists" not in spec:
            return None

        return AdditionalValidator(
            exists=[key for key in spec["exists"]],
        )


class TrackingNumberDefinition:
    """
    Represents a tracking number definition.

    Attributes:
        courier: The courier associated with this tracking number definition.
        product: The product or service type for the tracking number definition.
        number_regex: Regex pattern to match and parse the tracking number.
        tracking_url_template: Template for generating tracking URLs.
        serial_number_parser: Parser for extracting serial number from the tracking number.
        additional: List of additional information extractors.
        additional_validator: Validator for additional extracted information.
        checksum_validator: Validator for the tracking number's checksum digit.
    """

    courier: Courier
    product: Product
    number_regex: Pattern
    tracking_url_template: Optional[str]
    serial_number_parser: SerialNumberParser
    additional: List[Additional]
    additional_validator: Optional[AdditionalValidator]
    checksum_validator: Optional[ChecksumValidator]

    def __init__(
        self,
        courier: Courier,
        product: Product,
        number_regex: Pattern,
        tracking_url_template: Optional[str],
        serial_number_parser: SerialNumberParser,
        additional: List[Additional],
        additional_validator: Optional[AdditionalValidator],
        checksum_validator: Optional[ChecksumValidator],
    ):
        self.courier = courier
        self.product = product
        self.number_regex = number_regex
        self.tracking_url_template = tracking_url_template
        self.serial_number_parser = serial_number_parser
        self.additional = additional
        self.additional_validator = additional_validator
        self.checksum_validator = checksum_validator

    def __repr__(self):
        return repr_with_args(
            self,
            courier=self.courier,
            product=self.product,
            number_regex=self.number_regex,
            tracking_url_template=self.tracking_url_template,
            serial_number_parser=self.serial_number_parser,
            additional=self.additional,
            additional_validator=self.additional_validator,
            checksum_validator=self.checksum_validator,
        )

    @classmethod
    def from_spec(cls, courier: Courier, tn_spec: Spec) -> "TrackingNumberDefinition":
        product = Product(name=tn_spec["name"])
        tracking_url_template = tn_spec.get("tracking_url")
        number_regex = parse_regex(tn_spec["regex"])

        # Optional additional validation, that provides mappings to countries, mail classes, etc.
        additional_spec = tn_spec.get("additional")
        additional: List[Additional] = []
        if isinstance(additional_spec, list):
            for spec in additional_spec:
                additional.append(Additional.from_spec(spec))

        validation_spec = tn_spec["validation"]
        serial_number_parser = (
            UPSSerialNumberParser()
            if courier.code == "ups"
            else DefaultSerialNumberParser.from_spec(validation_spec)
        )

        # Additional validation that is required
        additional_validation_spec = validation_spec.get("additional")
        additional_validator = AdditionalValidator.from_spec(additional_validation_spec)

        return TrackingNumberDefinition(
            courier=courier,
            product=product,
            number_regex=number_regex,
            tracking_url_template=tracking_url_template,
            serial_number_parser=serial_number_parser,
            additional=additional,
            additional_validator=additional_validator,
            checksum_validator=ChecksumValidator.from_spec(validation_spec),
        )

    def test(self, tracking_number: str) -> Optional[TrackingNumber]:
        match = self.number_regex.fullmatch(tracking_number)
        if not match:
            return None

        match_data = match.groupdict() if match else {}
        serial_number = self._get_serial_number(match_data)
        tracking_url = self.tracking_url(tracking_number)

        additional: Dict[str, Info] = {}
        for addition in self.additional:
            info = self._get_additional(addition, match_data)
            if info:
                additional[addition.name] = info

        validation_errors = self._get_validation_errors(
            serial_number,
            additional,
            match_data,
        )

        return TrackingNumber(
            number=tracking_number,
            courier=self.courier,
            product=self.product,
            match_data=match_data,
            serial_number=serial_number,
            tracking_url=tracking_url,
            additional=additional,
            validation_errors=validation_errors,
        )

    def _get_serial_number(self, match_data: MatchData) -> Optional[SerialNumber]:
        raw_serial_number = match_data.get("SerialNumber")
        if raw_serial_number:
            return self.serial_number_parser.parse(
                _remove_whitespace(raw_serial_number),
            )

        return None

    def _get_validation_errors(
        self,
        serial_number: Optional[SerialNumber],
        additional: Dict[str, Info],
        match_data: MatchData,
    ) -> List[ValidationError]:
        errors: List[ValidationError] = []
        checksum_error = self._get_checksum_errors(serial_number, match_data)
        if checksum_error:
            errors.append(checksum_error)

        errors += self._get_additional_error(additional)

        return errors

    def _get_checksum_errors(
        self,
        serial_number: Optional[SerialNumber],
        match_data: MatchData,
    ) -> Optional[ValidationError]:
        if not self.checksum_validator:
            return None

        if not serial_number:
            return "checksum", "SerialNumber not found"

        check_digit = match_data.get("CheckDigit")
        if not check_digit:
            return "checksum", "CheckDigit not found"

        passes_checksum = self.checksum_validator.passes(
            serial_number=serial_number,
            check_digit=int(check_digit),
        )

        if not passes_checksum:
            return "checksum", "Checksum validation failed"

        return None

    def _get_additional(
        self,
        additional: Additional,
        match_data: MatchData,
    ) -> Optional[Info]:
        group_key = additional.regex_group_name
        raw_value = match_data.get(group_key)
        if not raw_value:
            # The group_key is not present in the match data
            return None

        value = _remove_whitespace(raw_value)
        for value_matcher, info in additional.value_matchers:
            if value_matcher.matches(value):
                return info

        # The group_key is present, but the value is not valid
        return None

    def _get_additional_error(
        self,
        additional: Dict[str, Info],
    ) -> List[ValidationError]:
        if not self.additional_validator:
            return []

        return [
            (key, f"{key} not found in additional information")
            for key in self.additional_validator.exists
            if key not in additional
        ]

    def tracking_url(self, tracking_number: str) -> Optional[str]:
        if not self.tracking_url_template:
            return None

        return self.tracking_url_template % tracking_number


def _remove_whitespace(value: str) -> str:
    return "".join(ch for ch in value if ch.strip())
