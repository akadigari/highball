import json
from pathlib import Path

import pytest

from lab.run_official_g1_rerun import (
    classify_gate_clearance,
    execute_official_rerun,
    reconcile_completed_receipt,
)


def _seed(root: Path) -> None:
    (root / "lab").mkdir(parents=True)
    (root / "out").mkdir()
    (root / "data" / "snapshots").mkdir(parents=True)
    (root / "SPEC.md").write_text("frozen spec\n")
    (root / "lab" / "run_g1.py").write_text("# frozen courtroom\n")
    (root / "data" / "ledger.csv").write_text("ts,action\n")
    (root / "data" / "snapshots" / "2026-08-01.jsonl").write_text("{}\n")
    gates = {
        "g1": {
            "mode": "OFFICIAL",
            "ran": "2026-08-06T02:05:37+00:00",
            "passed": False,
            "decisions": {},
        }
    }
    (root / "out" / "gates_status.json").write_text(json.dumps(gates))


def _successful_runner(root: Path) -> None:
    path = root / "out" / "gates_status.json"
    gates = json.loads(path.read_text())
    gates["g1"] = {
        "mode": "OFFICIAL",
        "ran": "2026-08-24T12:00:00+00:00",
        "passed": True,
        "decisions": {
            "d1_counted_clock": {
                "passed": True,
                "qualifying_cities": ["sea", "chi", "dal"],
            },
            "d3_honesty": {"override_fired": False},
        },
    }
    path.write_text(json.dumps(gates))


def test_requires_explicit_owner_authorization(tmp_path: Path) -> None:
    _seed(tmp_path)
    with pytest.raises(ValueError, match="owner-authorized"):
        execute_official_rerun(
            root=tmp_path,
            owner_authorized=False,
            authorization_note="owner call",
        )


def test_success_records_one_shot_receipt_and_frozen_inputs(tmp_path: Path) -> None:
    _seed(tmp_path)
    times = iter(["archive", "start", "finish"])
    receipt = execute_official_rerun(
        root=tmp_path,
        owner_authorized=True,
        authorization_note="User authorized the official rerun",
        runner=_successful_runner,
        now=lambda: next(times),
    )
    assert receipt["state"] == "COMPLETED"
    assert receipt["one_shot"]["consumed"] is True
    assert receipt["gate_clearance"] == {
        "d1_rule_met_before_honesty_override": True,
        "d1_qualifying_city_count": 3,
        "d3_cleared": True,
        "official_g1_passed": True,
    }
    assert receipt["boundaries"]["real_money"] == 0
    assert receipt["frozen_inputs"]["snapshots"]["count"] == 1
    assert (tmp_path / "out" / "g1_initial_official_archive.json").exists()


def test_completed_receipt_prevents_another_official_rerun(tmp_path: Path) -> None:
    _seed(tmp_path)
    times = iter(["archive", "start", "finish"])
    execute_official_rerun(
        root=tmp_path,
        owner_authorized=True,
        authorization_note="owner call",
        runner=_successful_runner,
        now=lambda: next(times),
    )
    with pytest.raises(RuntimeError, match="already consumed"):
        execute_official_rerun(
            root=tmp_path,
            owner_authorized=True,
            authorization_note="try again",
            runner=_successful_runner,
        )


def test_failed_attempt_stays_consumed_and_fail_closed(tmp_path: Path) -> None:
    _seed(tmp_path)

    def fail(_root: Path) -> None:
        raise RuntimeError("public source unavailable")

    times = iter(["archive", "start", "finish"])
    with pytest.raises(RuntimeError, match="public source unavailable"):
        execute_official_rerun(
            root=tmp_path,
            owner_authorized=True,
            authorization_note="owner call",
            runner=fail,
            now=lambda: next(times),
        )
    receipt = json.loads((tmp_path / "out" / "g1_official_rerun_receipt.json").read_text())
    assert receipt["state"] == "FAILED_CLOSED"
    assert receipt["one_shot"]["consumed"] is True


def test_raw_d1_is_reported_separately_when_d3_overrides_it() -> None:
    verdict = {
        "decisions": {
            "d1_counted_clock": {
                "qualifying_cities": ["sea", "chi", "dal", "okc", "nola"],
                "passed": False,
            },
            "d3_honesty": {"override_fired": True},
        }
    }
    assert classify_gate_clearance(verdict) == {
        "d1_rule_met_before_honesty_override": True,
        "d1_qualifying_city_count": 5,
        "d3_cleared": False,
        "official_g1_passed": False,
    }


def test_reconcile_updates_only_derived_clearance(tmp_path: Path) -> None:
    _seed(tmp_path)
    times = iter(["archive", "start", "finish"])
    receipt = execute_official_rerun(
        root=tmp_path,
        owner_authorized=True,
        authorization_note="owner call",
        runner=_successful_runner,
        now=lambda: next(times),
    )
    receipt["gate_clearance"] = {"stale": True}
    path = tmp_path / "out" / "g1_official_rerun_receipt.json"
    path.write_text(json.dumps(receipt))
    reconciled = reconcile_completed_receipt(root=tmp_path)
    assert reconciled["gate_clearance"]["d1_rule_met_before_honesty_override"] is True
    assert reconciled["gate_clearance"]["official_g1_passed"] is True
