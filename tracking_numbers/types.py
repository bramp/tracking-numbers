from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple


Info = Dict[str, Any]
Spec = Dict[str, Any]
SerialNumber = List[str]
ValidationError = Tuple[str, str]


@dataclass
class Product:
    name: str


@dataclass
class Courier:
    code: str
    name: str


@dataclass
class TrackingNumber:
    number: str
    courier: Courier
    product: Product
    serial_number: Optional[SerialNumber]
    tracking_url: Optional[str]
    match_data: Info
    additional: Dict[str, Info]
    validation_errors: List[ValidationError]

    @property
    def valid(self) -> bool:
        return not self.validation_errors

    @property
    def courier_info(self) -> Info:
        """Provides information about the courier.

        Returns:
            Info: A dictionary containing courier information. Typical fields
            include "country", "courier", and "courier_url".
        """
        # Start with dataclass fields
        info = {
            "code": self.courier.code,
            "name": self.courier.name,
        }
        # Merge in additional fields if present
        additional = self.additional.get("Courier", {})
        for k, v in additional.items():
            if v is None:
                continue
            if k == "courier":
                info["name"] = v
            elif k == "courier_url":
                info["url"] = v
            else:
                info[k] = v
        return info

    @property
    def service_type(self) -> Info:
        """Provides additional information about the service type.

        Returns:
            Info: A dictionary containing service type information. Typical fields
            include "name", and "description".
        """
        return {"code": self.match_data.get("ServiceType")} | self.additional.get(
            "Service Type",
            {},
        )


def to_int(serial_number: SerialNumber) -> int:
    return int("".join(map(str, serial_number)))
