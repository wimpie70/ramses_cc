"""Test R51: Schema stripping parity (config_flow vs gateway).

Verifies that the schema stripping used by config_flow validation
(``strip_traits_for_validation``) produces the same result as what
the gateway actually receives (``_strip_schema_extensions``).  Both
paths go through ``_strip_and_orchestrate``, so they must be identical.

Converted from ha_sim_test recipe R51 (structural) to a pytest unit test.

See: https://github.com/ramses-rf/ramses_cc/issues/767
"""

from __future__ import annotations

import json

from custom_components.ramses_cc.coordinator import RamsesCoordinator
from custom_components.ramses_cc.schemas import strip_traits_for_validation

CTL = "01:150000"
DHW = "07:150000"
FAN = "32:150000"
REM = "37:170000"
TRV = "04:150003"

TEST_SCHEMA = {
    CTL: {
        "zones": {
            "03": {
                "sensor": "01:150003",
                "actuators": [TRV],
                "_name": "Lounge",
            },
        },
        "stored_hotwater": {"sensor": DHW},
        "_class": "CTL",
        "_alias": "Main Controller",
        "_owner": "home",
    },
    TRV: {
        "_class": "TRV",
        "_disabled": False,
        "_commands": {"off": {"code": "2309", "payload": "0000FF"}},
        "_name": "Lounge TRV",
    },
    DHW: {
        "_class": "DHW",
        "_faked": True,
    },
    FAN: {
        "remotes": [REM],
        "_class": "FAN",
        "_bound": REM,
        "_scheme": "itho",
    },
    REM: {
        "_class": "REM",
        "_commands": {"turn_on": {"code": "22F1", "payload": "000100"}},
    },
    "_owner": "home",
    "orphans_heat": [],
    "orphans_hvac": [],
}


def _serialize(d: object) -> str:
    return json.dumps(d, sort_keys=True, default=str)


def _find_underscore_keys(obj: object, path: str = "") -> list[str]:
    """Recursively find _-prefixed keys (except _name in zone entries)."""
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.startswith("_"):
                # _name is allowed in zone entries (under .zones.<idx>)
                if k == "_name" and ".zones." in path:
                    pass
                else:
                    found.append(f"{path}.{k}" if path else k)
            found.extend(_find_underscore_keys(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(_find_underscore_keys(v, f"{path}[{i}]"))
    return found


# Run both stripping paths once at module level
_VALIDATED = strip_traits_for_validation(dict(TEST_SCHEMA))
_GATEWAY = RamsesCoordinator._strip_schema_extensions(dict(TEST_SCHEMA))


def test_stripping_functions_run_without_error() -> None:
    """stripping functions run without error."""
    assert _VALIDATED is not None
    assert _GATEWAY is not None


def test_config_flow_and_gateway_produce_identical_schema() -> None:
    """config_flow and gateway stripping produce identical schema."""
    assert _serialize(_VALIDATED) == _serialize(_GATEWAY)


def test_no_underscore_keys_in_validated() -> None:
    """no _-prefixed keys in validated schema."""
    keys = _find_underscore_keys(_VALIDATED, "validated")
    assert not keys, f"found: {keys[:5]}"


def test_no_underscore_keys_in_gateway() -> None:
    """no _-prefixed keys in gateway schema."""
    keys = _find_underscore_keys(_GATEWAY, "gateway")
    assert not keys, f"found: {keys[:5]}"


def test_validated_has_ctl_with_zones() -> None:
    """validated schema has CTL with zones."""
    ctl = _VALIDATED.get(CTL, {})
    assert "zones" in ctl


def test_gateway_has_ctl_with_zones() -> None:
    """gateway schema has CTL with zones."""
    ctl = _GATEWAY.get(CTL, {})
    assert "zones" in ctl


def test_validated_has_ctl() -> None:
    """CTL in validated."""
    assert CTL in _VALIDATED


def test_gateway_has_ctl() -> None:
    """CTL in gateway."""
    assert CTL in _GATEWAY


def test_validated_has_fan() -> None:
    """FAN in validated."""
    assert FAN in _VALIDATED


def test_gateway_has_fan() -> None:
    """FAN in gateway."""
    assert FAN in _GATEWAY
