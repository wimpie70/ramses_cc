"""Test R52: known_list derivation from schema (_derive_known_list_from_schema).

Verifies that ``RamsesCoordinator._derive_known_list_from_schema`` correctly:
- Extracts all device IDs from the schema topology (CTL, zones, DHW, FAN, REMs)
- Maps _-prefixed traits to native names (_class→class, _alias→alias, etc.)
- Excludes _skipped devices
- Includes _disabled devices (so ramses_rf doesn't reject their packets)
- Excludes foreign-owner devices (different _owner than root _owner)

Converted from ha_sim_test recipe R52 (structural) to a pytest unit test.

See: https://github.com/ramses-rf/ramses_cc/issues/767
"""

from __future__ import annotations

from custom_components.ramses_cc.coordinator import RamsesCoordinator

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
            },
        },
        "stored_hotwater": {"sensor": DHW},
        "_class": "CTL",
        "_alias": "Main Controller",
        "_owner": "home",
    },
    TRV: {
        "_class": "TRV",
        "_name": "Lounge TRV",
        "_alias": "Override Name",
        "_disabled": True,
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
    },
    "04:150099": {
        "_class": "TRV",
        "_skipped": True,
    },
    "04:150088": {
        "_class": "TRV",
        "_owner": "neighbour",
    },
    "_owner": "home",
    "orphans_heat": [],
    "orphans_hvac": [],
}

# Run derivation once at module level
_KL = RamsesCoordinator._derive_known_list_from_schema(dict(TEST_SCHEMA))


def test_derive_runs_without_error() -> None:
    """_derive_known_list_from_schema runs without error."""
    assert _KL is not None


def test_ctl_in_known_list() -> None:
    """CTL in known_list."""
    assert CTL in _KL


def test_ctl_class_derived() -> None:
    """CTL class derived from _class."""
    assert _KL.get(CTL, {}).get("class") == "CTL"


def test_ctl_alias_derived() -> None:
    """CTL alias derived from _alias."""
    assert _KL.get(CTL, {}).get("alias") == "Main Controller"


def test_trv_included_despite_disabled() -> None:
    """TRV included despite _disabled."""
    assert TRV in _KL


def test_trv_class_derived() -> None:
    """TRV class derived from _class."""
    assert _KL.get(TRV, {}).get("class") == "TRV"


def test_trv_alias_from_schema() -> None:
    """TRV alias from schema _alias."""
    assert _KL.get(TRV, {}).get("alias") == "Override Name"


def test_dhw_in_known_list() -> None:
    """DHW in known_list."""
    assert DHW in _KL


def test_dhw_faked_derived() -> None:
    """DHW faked derived from _faked."""
    assert _KL.get(DHW, {}).get("faked") is True


def test_fan_in_known_list() -> None:
    """FAN in known_list."""
    assert FAN in _KL


def test_fan_class_derived() -> None:
    """FAN class derived from _class."""
    assert _KL.get(FAN, {}).get("class") == "FAN"


def test_fan_bound_derived() -> None:
    """FAN bound derived from _bound."""
    assert _KL.get(FAN, {}).get("bound") == REM


def test_fan_scheme_derived() -> None:
    """FAN scheme derived from _scheme."""
    assert _KL.get(FAN, {}).get("scheme") == "itho"


def test_rem_in_known_list() -> None:
    """REM in known_list (from FAN remotes)."""
    assert REM in _KL


def test_rem_class_derived() -> None:
    """REM class derived from _class."""
    assert _KL.get(REM, {}).get("class") == "REM"


def test_zone_sensor_in_known_list() -> None:
    """zone sensor 01:150003 in known_list."""
    assert "01:150003" in _KL


def test_skipped_device_excluded() -> None:
    """_skipped device excluded from known_list."""
    assert "04:150099" not in _KL


def test_foreign_owner_device_excluded() -> None:
    """foreign-owner device excluded from known_list."""
    assert "04:150088" not in _KL
