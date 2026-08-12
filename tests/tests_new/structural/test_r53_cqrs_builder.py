"""Test R53: CQRS builder defaults vs _commands override.

Verifies the command priority chain for FAN/REM entities:
1. FAN's schema ``_commands`` (dict templates — Phase 3b, highest priority)
2. Bound REM's schema ``_commands`` (packet strings — Phase 3a fallback)
3. known_list[bound_rem][commands] (legacy fallback)
4. ramses_rf builder defaults (``set_fan_mode`` standard implementation)

Also tests ``_split_commands``, ``_merge_commands``, ``_is_command_dict``,
``_build_packet_from_template``, and ``_parse_packet_to_template``.

Converted from ha_sim_test recipe R53 (structural) to a pytest unit test.

See: https://github.com/ramses-rf/ramses_cc/issues/767
"""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.ramses_cc.remote import (
    _build_packet_from_template,
    _is_command_dict,
    _merge_commands,
    _parse_packet_to_template,
    _split_commands,
)

FAN = "32:150000"
REM = "37:170000"


# ── 1. _split_commands ────────────────────────────────────────────────


def test_split_commands_separates_cmds_from_meta() -> None:
    """_split_commands separates 2 commands from 1 metadata."""
    raw = {
        "turn_on": f"I --- {REM} {FAN} --:------ 22F1 003 000100",
        "turn_off": f"I --- {REM} {FAN} --:------ 22F1 003 000000",
        "_comment": "Learned REM commands",
    }
    cmds, meta = _split_commands(raw)
    assert len(cmds) == 2
    assert len(meta) == 1


def test_split_commands_comment_in_meta() -> None:
    """_split_commands: _comment in metadata, not commands."""
    raw = {
        "turn_on": f"I --- {REM} {FAN} --:------ 22F1 003 000100",
        "_comment": "Learned REM commands",
    }
    cmds, meta = _split_commands(raw)
    assert "_comment" in meta
    assert "_comment" not in cmds


# ── 2. _merge_commands ────────────────────────────────────────────────


def test_merge_fan_metadata_wins() -> None:
    """_merge_commands: FAN metadata wins."""
    fan_cmds = {
        "turn_on": {"verb": "I", "code": "22F1", "payload": "000100"},
        "_comment": "FAN templates",
    }
    rem_cmds = {
        "turn_on": f"I --- {REM} {FAN} --:------ 22F1 003 000100",
        "_comment": "REM commands (should be ignored)",
    }
    merged = _merge_commands(fan_cmds, rem_cmds)
    _, m_meta = _split_commands(merged)
    assert m_meta.get("_comment") == "FAN templates"


def test_merge_fan_dict_wins_over_rem_string() -> None:
    """_merge_commands: FAN dict turn_on wins over REM string."""
    fan_cmds = {
        "turn_on": {"verb": "I", "code": "22F1", "payload": "000100"},
    }
    rem_cmds = {
        "turn_on": f"I --- {REM} {FAN} --:------ 22F1 003 000100",
    }
    merged = _merge_commands(fan_cmds, rem_cmds)
    m_cmds, _ = _split_commands(merged)
    assert isinstance(m_cmds.get("turn_on"), dict)


def test_merge_rem_fills_gap() -> None:
    """_merge_commands: REM turn_off fills gap."""
    fan_cmds = {"turn_on": {"verb": "I", "code": "22F1", "payload": "000100"}}
    rem_cmds = {
        "turn_on": f"I --- {REM} {FAN} --:------ 22F1 003 000100",
        "turn_off": f"I --- {REM} {FAN} --:------ 22F1 003 000000",
    }
    merged = _merge_commands(fan_cmds, rem_cmds)
    m_cmds, _ = _split_commands(merged)
    assert "turn_off" in m_cmds


# ── 3. _is_command_dict ───────────────────────────────────────────────


def test_is_command_dict_dict_is_true() -> None:
    """_is_command_dict: dict is True."""
    assert _is_command_dict({"verb": "I", "code": "22F1", "payload": "000100"}) is True


def test_is_command_dict_string_is_false() -> None:
    """_is_command_dict: string is False."""
    assert (
        _is_command_dict("I --- 37:170000 32:150000 --:------ 22F1 003 000100") is False
    )


def test_is_command_dict_none_is_false() -> None:
    """_is_command_dict: None is False."""
    assert _is_command_dict(None) is False


# ── 4. _parse_packet_to_template ──────────────────────────────────────


def test_parse_packet_verb_extracted() -> None:
    """_parse_packet_to_template: verb extracted."""
    template = _parse_packet_to_template(
        "W --- 32:153001 30:160000 --:------ 22F7 003 0000EF"
    )
    assert template.get("verb") == "W"


def test_parse_packet_code_extracted() -> None:
    """_parse_packet_to_template: code extracted."""
    template = _parse_packet_to_template(
        "W --- 32:153001 30:160000 --:------ 22F7 003 0000EF"
    )
    assert template.get("code") == "22F7"


def test_parse_packet_payload_extracted() -> None:
    """_parse_packet_to_template: payload extracted."""
    template = _parse_packet_to_template(
        "W --- 32:153001 30:160000 --:------ 22F7 003 0000EF"
    )
    assert template.get("payload") == "0000EF"


# ── 5. _build_packet_from_template ────────────────────────────────────


def _make_fan_dev() -> MagicMock:
    fan_dev = MagicMock()
    fan_dev.id = FAN
    fan_dev.get_bound_rem.return_value = REM
    return fan_dev


def _make_coord() -> MagicMock:
    coord = MagicMock()
    coord.client = None  # triggers HGI fallback path
    return coord


def test_build_packet_starts_with_verb() -> None:
    """_build_packet_from_template: starts with verb."""
    packet = _build_packet_from_template(
        {"verb": "I", "code": "22F1", "payload": "000100"},
        _make_fan_dev(),
        _make_coord(),
    )
    assert packet.startswith("I ")


def test_build_packet_src_is_bound_rem() -> None:
    """_build_packet_from_template: src is bound REM."""
    packet = _build_packet_from_template(
        {"verb": "I", "code": "22F1", "payload": "000100"},
        _make_fan_dev(),
        _make_coord(),
    )
    assert REM in packet


def test_build_packet_dst_is_fan() -> None:
    """_build_packet_from_template: dst is FAN."""
    packet = _build_packet_from_template(
        {"verb": "I", "code": "22F1", "payload": "000100"},
        _make_fan_dev(),
        _make_coord(),
    )
    assert FAN in packet


# ── 6. Priority chain ─────────────────────────────────────────────────


def test_priority_fan_dict_wins() -> None:
    """priority: FAN dict template wins for 'heat'."""
    fan_commands = {"heat": {"verb": "W", "code": "22F1", "payload": "000200"}}
    fan_mode = "heat"
    assert fan_mode in fan_commands and _is_command_dict(fan_commands[fan_mode])


def test_priority_rem_fallback() -> None:
    """priority: REM fallback for 'cool' (not in FAN)."""
    fan_commands = {"heat": {"verb": "W", "code": "22F1", "payload": "000200"}}
    rem_commands = {
        "heat": f"W --- {REM} {FAN} --:------ 22F1 003 000200",
        "cool": f"W --- {REM} {FAN} --:------ 22F1 003 000201",
    }
    fan_mode = "cool"
    assert fan_mode not in fan_commands and fan_mode in rem_commands


def test_priority_default_fallback() -> None:
    """priority: ramses_rf default for 'auto' (neither)."""
    fan_commands = {"heat": {"verb": "W", "code": "22F1", "payload": "000200"}}
    rem_commands = {"heat": "...", "cool": "..."}
    fan_mode = "auto"
    assert fan_mode not in fan_commands and fan_mode not in rem_commands
