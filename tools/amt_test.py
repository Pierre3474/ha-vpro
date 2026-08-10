#!/usr/bin/env python3
"""Standalone AMT protocol validator — run BEFORE trusting the HA integration.

Usage:
  python3 amt_test.py <host> <user> <password> [--port 16993] [--no-tls] [--action on|off|reset|cycle|bios]

Reads power state + AMT versions. Optional power action with confirmation.
Imports the same amt.py the HA integration uses, so a green run here means the
HA integration's protocol layer is sound.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "vpro"))
import amt  # noqa: E402

ACTIONS = {
    "on": amt.POWER_ON,
    "off": amt.POWER_OFF_SOFT,
    "reset": amt.POWER_RESET,
    "cycle": amt.POWER_CYCLE_SOFT,
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("host")
    p.add_argument("user")
    p.add_argument("password")
    p.add_argument("--port", type=int, default=16993)
    p.add_argument("--no-tls", action="store_true")
    p.add_argument("--action", choices=[*ACTIONS, "bios"])
    a = p.parse_args()

    import urllib3
    urllib3.disable_warnings()

    c = amt.AMTClient(a.host, a.user, a.password, port=a.port, use_tls=not a.no_tls)

    try:
        state = c.get_power_state()
    except amt.AMTError as e:
        print(f"[FAIL] power state: {e}")
        return 1
    print(f"[OK] power state (CIM) = {state}")

    try:
        versions = c.get_versions()
        print(f"[OK] versions = {versions}")
    except amt.AMTError as e:
        print(f"[warn] versions: {e}")

    if a.action:
        if input(f"Send '{a.action}' to {a.host}? [y/N] ").lower() != "y":
            print("aborted")
            return 0
        try:
            ok = c.boot_to_bios() if a.action == "bios" else c.set_power(ACTIONS[a.action])
            print(f"[{'OK' if ok else 'FAIL'}] action '{a.action}' -> {ok}")
        except amt.AMTError as e:
            print(f"[FAIL] action: {e}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
