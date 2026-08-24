"""Consume Highball's single owner-authorized official G1 rerun.

The frozen SPEC addendum 12 allows a future official G1 rerun only after an
owner call. This wrapper records that call, archives the first official result,
and creates a one-shot receipt before invoking the unchanged courtroom.

Usage:
    python3 lab/run_official_g1_rerun.py \
        --owner-authorized \
        --authorization-note "User authorized all in-scope work on 2026-08-24"
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parent.parent
RECEIPT_NAME = "g1_official_rerun_receipt.json"
ARCHIVE_NAME = "g1_initial_official_archive.json"


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _snapshot_manifest(root: Path) -> dict:
    snapshots = sorted((root / "data" / "snapshots").glob("*.jsonl"))
    digest = hashlib.sha256()
    for path in snapshots:
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(_sha256(path).encode())
        digest.update(b"\n")
    return {
        "count": len(snapshots),
        "first": snapshots[0].name if snapshots else None,
        "last": snapshots[-1].name if snapshots else None,
        "manifest_sha256": digest.hexdigest(),
    }


def _run_courtroom(root: Path) -> None:
    subprocess.run(
        [sys.executable, "lab/run_g1.py", "--official"],
        cwd=root,
        check=True,
    )


def classify_gate_clearance(verdict: dict) -> dict:
    """Separate raw D1 evidence from the D3-overridden counted clock."""
    decisions = verdict.get("decisions", {})
    d1 = decisions.get("d1_counted_clock", {})
    d3 = decisions.get("d3_honesty", {})
    qualifying = d1.get("qualifying_cities", [])
    d1_rule_met = isinstance(qualifying, list) and len(qualifying) >= 3
    d3_cleared = d3.get("override_fired") is False
    return {
        "d1_rule_met_before_honesty_override": d1_rule_met,
        "d1_qualifying_city_count": len(qualifying) if isinstance(qualifying, list) else 0,
        "d3_cleared": d3_cleared,
        "official_g1_passed": d1_rule_met and d3_cleared,
    }


def reconcile_completed_receipt(*, root: Path = ROOT) -> dict:
    """Recompute derived clearance labels without consuming another rerun."""
    receipt_path = root / "out" / RECEIPT_NAME
    receipt = json.loads(receipt_path.read_text())
    if receipt.get("state") != "COMPLETED" or not isinstance(receipt.get("after"), dict):
        raise RuntimeError("only a completed official rerun receipt can be reconciled")
    receipt["gate_clearance"] = classify_gate_clearance(receipt["after"])
    _atomic_json(receipt_path, receipt)
    return receipt


def execute_official_rerun(
    *,
    root: Path = ROOT,
    owner_authorized: bool,
    authorization_note: str,
    runner: Callable[[Path], None] = _run_courtroom,
    now: Callable[[], str] = _utc_now,
) -> dict:
    """Run once, fail closed, and return the completed audit receipt."""
    if not owner_authorized:
        raise ValueError("explicit --owner-authorized is required")
    if not authorization_note.strip():
        raise ValueError("a non-empty authorization note is required")

    gates_path = root / "out" / "gates_status.json"
    receipt_path = root / "out" / RECEIPT_NAME
    archive_path = root / "out" / ARCHIVE_NAME
    if receipt_path.exists():
        state = json.loads(receipt_path.read_text()).get("state", "UNKNOWN")
        raise RuntimeError(f"official G1 rerun already consumed: {state}")

    gates = json.loads(gates_path.read_text())
    before = gates.get("g1")
    if not isinstance(before, dict) or before.get("mode") != "OFFICIAL":
        raise RuntimeError("the first official G1 result is missing")
    if before.get("passed") is not False:
        raise RuntimeError("the first official G1 did not fail, so no rerun is admissible")

    if archive_path.exists():
        archived = json.loads(archive_path.read_text())
        if archived.get("g1") != before:
            raise RuntimeError("initial official G1 archive conflicts with current gate")
    else:
        _atomic_json(
            archive_path,
            {
                "schema_version": 1,
                "archived_at": now(),
                "source": "out/gates_status.json#g1",
                "g1": before,
            },
        )

    inputs = {
        "spec_sha256": _sha256(root / "SPEC.md"),
        "courtroom_sha256": _sha256(root / "lab" / "run_g1.py"),
        "ledger_sha256": _sha256(root / "data" / "ledger.csv"),
        "snapshots": _snapshot_manifest(root),
    }
    started_at = now()
    receipt = {
        "schema_version": 1,
        "kind": "highball_official_g1_rerun",
        "state": "STARTED",
        "started_at": started_at,
        "authorization": {
            "owner_authorized": True,
            "note": authorization_note.strip(),
        },
        "one_shot": {
            "allowed_runs": 1,
            "automatic_rerun_allowed": False,
            "consumed": True,
        },
        "boundaries": {
            "keyless_public_data_only": True,
            "sim_only": True,
            "network_orders": 0,
            "broker_orders": 0,
            "real_money": 0,
        },
        "frozen_inputs": inputs,
        "before": before,
    }
    _atomic_json(receipt_path, receipt)

    try:
        runner(root)
        after = json.loads(gates_path.read_text()).get("g1")
        if not isinstance(after, dict) or after.get("mode") != "OFFICIAL":
            raise RuntimeError("courtroom did not write an official result")
        if after.get("ran") == before.get("ran"):
            raise RuntimeError("courtroom did not write a fresh official result")
        clearance = classify_gate_clearance(after)
        passed = clearance["official_g1_passed"]
        if after.get("passed") is not passed:
            raise RuntimeError("official verdict disagrees with the frozen D1 and D3 gates")
    except Exception as exc:
        receipt.update(
            {
                "state": "FAILED_CLOSED",
                "finished_at": now(),
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        _atomic_json(receipt_path, receipt)
        raise

    receipt.update(
        {
            "state": "COMPLETED",
            "finished_at": now(),
            "after": after,
            "gate_clearance": clearance,
        }
    )
    _atomic_json(receipt_path, receipt)
    return receipt


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-authorized", action="store_true")
    parser.add_argument("--authorization-note", default="")
    parser.add_argument("--reconcile-receipt", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.reconcile_receipt:
        print(json.dumps(reconcile_completed_receipt(), indent=2, sort_keys=True))
        return
    receipt = execute_official_rerun(
        owner_authorized=args.owner_authorized,
        authorization_note=args.authorization_note,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
