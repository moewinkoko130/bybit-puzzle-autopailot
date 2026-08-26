from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReconciliationMismatch:
    key: str
    local: dict | None
    remote: dict | None
    reason: str


def _key(position: dict[str, Any]) -> str:
    return str(position.get("orderId") or position.get("positionIdx") or position.get("side"))


def reconcile_positions(local_positions: list[dict], remote_positions: list[dict]) -> list[ReconciliationMismatch]:
    local_by_key = {_key(position): position for position in local_positions}
    remote_by_key = {_key(position): position for position in remote_positions}
    mismatches: list[ReconciliationMismatch] = []
    for key in sorted(local_by_key.keys() - remote_by_key.keys()):
        mismatches.append(ReconciliationMismatch(key, local_by_key[key], None, "missing_remote_position"))
    for key in sorted(remote_by_key.keys() - local_by_key.keys()):
        mismatches.append(ReconciliationMismatch(key, None, remote_by_key[key], "missing_local_position"))
    for key in sorted(local_by_key.keys() & remote_by_key.keys()):
        local = local_by_key[key]
        remote = remote_by_key[key]
        if str(local.get("size")) != str(remote.get("size")) or local.get("side") != remote.get("side"):
            mismatches.append(ReconciliationMismatch(key, local, remote, "position_quantity_or_side_mismatch"))
    return mismatches


def reconcile_orders(local_orders: list[dict], remote_orders: list[dict]) -> list[ReconciliationMismatch]:
    local_by_key = {_key(order): order for order in local_orders}
    remote_by_key = {_key(order): order for order in remote_orders}
    mismatches: list[ReconciliationMismatch] = []
    for key in sorted(local_by_key.keys() - remote_by_key.keys()):
        mismatches.append(ReconciliationMismatch(key, local_by_key[key], None, "missing_remote_order"))
    for key in sorted(remote_by_key.keys() - local_by_key.keys()):
        mismatches.append(ReconciliationMismatch(key, None, remote_by_key[key], "missing_local_order"))
    for key in sorted(local_by_key.keys() & remote_by_key.keys()):
        local = local_by_key[key]
        remote = remote_by_key[key]
        if local.get("orderStatus") != remote.get("orderStatus") or local.get("cumExecQty") != remote.get("cumExecQty"):
            mismatches.append(ReconciliationMismatch(key, local, remote, "order_status_or_fill_mismatch"))
    return mismatches
