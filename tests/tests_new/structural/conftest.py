"""Conftest for structural tests in ramses_cc.

These tests inspect the source code structure of ramses_cc without
needing a running HA instance.  They are the pytest equivalents of
the ha_sim_test structural recipes (R51, R52, R53).

The ``custom_components`` directory is a namespace package — pytest
run from the repo root will find it automatically.
"""
