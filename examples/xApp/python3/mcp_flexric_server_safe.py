# mcp_flexric_server.py
import os
import json
import time
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests
from mcp.server.fastmcp import FastMCP

# -------------------------
# Config (env-based)
# -------------------------
XAPP_URL = os.environ.get("XAPP_URL", "http://127.0.0.1:8088")
TIMEOUT_S = float(os.environ.get("XAPP_TIMEOUT_S", "1.5"))

# Allowlist: comma-separated E2 node IDs. Example:
# export E2_NODE_ALLOWLIST="gnb_001,gnb_002"
ALLOWLIST_RAW = os.environ.get("E2_NODE_ALLOWLIST", "").strip()
E2_NODE_ALLOWLIST = {s.strip() for s in ALLOWLIST_RAW.split(",") if s.strip()}

# PRB bounds (sane defaults for many NR configs; adjust to your deployment)
# You can set PRB_MAX=275 for 100MHz@30kHz, etc.
PRB_MIN = int(os.environ.get("PRB_MIN", "0"))
PRB_MAX = int(os.environ.get("PRB_MAX", "275"))

# Rate limit for control tools
# Example: 2 tokens/sec with burst 3 => at most ~3 rapid controls then 2/s
CTRL_RATE_TOKENS_PER_SEC = float(os.environ.get("CTRL_RATE_TOKENS_PER_SEC", "2.0"))
CTRL_RATE_BURST = float(os.environ.get("CTRL_RATE_BURST", "3.0"))

# Audit log path (JSON lines)
AUDIT_PATH = os.environ.get("AUDIT_LOG_PATH", "./mcp_flexric_audit.jsonl")

# If you want to disable all control tools quickly:
CONTROL_ENABLED = os.environ.get("CONTROL_ENABLED", "1").strip() not in ("0", "false", "False")

# -------------------------
# HTTP helpers
# -------------------------
def _get(path: str, params: Optional[dict] = None) -> Dict[str, Any]:
    r = requests.get(f"{XAPP_URL}{path}", params=params, timeout=TIMEOUT_S)
    r.raise_for_status()
    return r.json()

def _post(path: str, payload: dict) -> Dict[str, Any]:
    r = requests.post(f"{XAPP_URL}{path}", json=payload, timeout=TIMEOUT_S)
    r.raise_for_status()
    return r.json()

# -------------------------
# Audit logging (JSONL)
# -------------------------
_audit_lock = threading.Lock()

def audit_log(event: Dict[str, Any]) -> None:
    event = dict(event)
    event["ts_ms"] = int(time.time() * 1000)
    with _audit_lock:
        with open(AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

# -------------------------
# Allowlist enforcement
# -------------------------
class PolicyError(Exception):
    pass

def enforce_allowlist(e2_node_id: str) -> None:
    if not E2_NODE_ALLOWLIST:
        # Empty allowlist means "allow all" by default. If you prefer "deny all unless set",
        # change this behavior.
        return
    if e2_node_id not in E2_NODE_ALLOWLIST:
        raise PolicyError(f"e2_node_id '{e2_node_id}' is not in allowlist")

# -------------------------
# PRB checks
# -------------------------
def validate_prb_range(pos_low: int, pos_high: int) -> None:
    if not (PRB_MIN <= pos_low <= PRB_MAX):
        raise PolicyError(f"pos_low {pos_low} out of bounds [{PRB_MIN}, {PRB_MAX}]")
    if not (PRB_MIN <= pos_high <= PRB_MAX):
        raise PolicyError(f"pos_high {pos_high} out of bounds [{PRB_MIN}, {PRB_MAX}]")
    if pos_low > pos_high:
        raise PolicyError(f"pos_low {pos_low} > pos_high {pos_high}")
    # Optional: enforce minimum width (avoid tiny slices that can destabilize schedulers)
    # if (pos_high - pos_low + 1) < 5:
    #     raise PolicyError("slice width too small (<5 PRBs)")

# -------------------------
# Rate limiter (token bucket)
# -------------------------
@dataclass
class TokenBucket:
    rate: float      # tokens per second
    capacity: float  # max tokens
    tokens: float
    last_ts: float
    lock: threading.Lock

    @classmethod
    def create(cls, rate: float, capacity: float) -> "TokenBucket":
        now = time.monotonic()
        return cls(rate=rate, capacity=capacity, tokens=capacity, last_ts=now, lock=threading.Lock())

    def consume(self, cost: float = 1.0) -> Tuple[bool, float]:
        """Return (allowed, retry_after_seconds)."""
        with self.lock:
            now = time.monotonic()
            elapsed = max(0.0, now - self.last_ts)
            self.last_ts = now

            # refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

            if self.tokens >= cost:
                self.tokens -= cost
                return True, 0.0

            needed = cost - self.tokens
            retry_after = needed / self.rate if self.rate > 0 else 9999.0
            return False, retry_after

CTRL_BUCKET = TokenBucket.create(rate=CTRL_RATE_TOKENS_PER_SEC, capacity=CTRL_RATE_BURST)

def enforce_rate_limit(tool_name: str) -> None:
    ok, retry_after = CTRL_BUCKET.consume(1.0)
    if not ok:
        raise PolicyError(f"rate_limited: retry_after={retry_after:.2f}s for tool={tool_name}")

# -------------------------
# Dry run helper
# -------------------------
def maybe_dry_run(tool_name: str, payload: dict, dry_run: bool) -> Dict[str, Any]:
    if dry_run:
        return {
            "dry_run": True,
            "tool": tool_name,
            "would_post": payload,
        }
    return {}

# -------------------------
# MCP tools
# -------------------------
mcp = FastMCP("flexric-oran-tools-safe")

@mcp.tool()
def ric_health() -> Dict[str, Any]:
    """Check xApp RPC health."""
    try:
        res = _get("/health")
        audit_log({"tool": "ric_health", "ok": True})
        return res
    except Exception as e:
        audit_log({"tool": "ric_health", "ok": False, "error": str(e)})
        raise

@mcp.tool()
def ric_list_e2_nodes() -> Dict[str, Any]:
    """List connected E2 nodes as seen by FlexRIC."""
    try:
        res = _get("/e2/nodes")
        audit_log({"tool": "ric_list_e2_nodes", "ok": True})
        # Optional: if allowlist is set, filter returned nodes to reduce agent temptation
        if E2_NODE_ALLOWLIST and "nodes" in res:
            res["nodes"] = [n for n in res["nodes"] if n.get("id") in E2_NODE_ALLOWLIST]
            res["allowlist_active"] = True
        return res
    except Exception as e:
        audit_log({"tool": "ric_list_e2_nodes", "ok": False, "error": str(e)})
        raise

@mcp.tool()
def slice_subscribe(e2_node_id: str, interval_ms: int = 10, dry_run: bool = False) -> Dict[str, Any]:
    """Subscribe to SLICE SM indications for a node."""
    tool = "slice_subscribe"
    event = {"tool": tool, "params": {"e2_node_id": e2_node_id, "interval_ms": interval_ms, "dry_run": dry_run}}
    try:
        enforce_allowlist(e2_node_id)
        payload = {"e2_node_id": e2_node_id, "interval_ms": interval_ms}
        dr = maybe_dry_run(tool, payload, dry_run)
        if dr:
            event.update({"ok": True, "dry_run": True})
            audit_log(event)
            return dr
        res = _post("/slice/subscribe", payload)
        event.update({"ok": True, "result": {"sub_id": res.get("sub_id")}})
        audit_log(event)
        return res
    except PolicyError as pe:
        event.update({"ok": False, "denied": True, "reason": str(pe)})
        audit_log(event)
        return {"ok": False, "denied": True, "reason": str(pe)}
    except Exception as e:
        event.update({"ok": False, "error": str(e)})
        audit_log(event)
        raise

@mcp.tool()
def slice_poll(sub_id: str, max_items: int = 200) -> Dict[str, Any]:
    """Poll cached SLICE SM indications."""
    tool = "slice_poll"
    event = {"tool": tool, "params": {"sub_id": sub_id, "max_items": max_items}}
    try:
        res = _post("/slice/poll", {"sub_id": sub_id, "max_items": max_items})
        event.update({"ok": True, "result": {"n": len(res.get("items", [])), "remaining": res.get("remaining")}})
        audit_log(event)
        return res
    except Exception as e:
        event.update({"ok": False, "error": str(e)})
        audit_log(event)
        raise

@mcp.tool()
def slice_unsubscribe(sub_id: str, dry_run: bool = False) -> Dict[str, Any]:
    """Remove SLICE SM subscription."""
    tool = "slice_unsubscribe"
    event = {"tool": tool, "params": {"sub_id": sub_id, "dry_run": dry_run}}
    try:
        payload = {"sub_id": sub_id}
        dr = maybe_dry_run(tool, payload, dry_run)
        if dr:
            event.update({"ok": True, "dry_run": True})
            audit_log(event)
            return dr
        res = _post("/slice/unsubscribe", payload)
        event.update({"ok": True})
        audit_log(event)
        return res
    except Exception as e:
        event.update({"ok": False, "error": str(e)})
        audit_log(event)
        raise

@mcp.tool()
def slice_set_static(
    e2_node_id: str,
    dl_slice_id: int, dl_pos_low: int, dl_pos_high: int,
    ul_slice_id: int, ul_pos_low: int, ul_pos_high: int,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Apply a simple static slice config (control). Agent-safe guarded.
    """
    tool = "slice_set_static"
    event = {"tool": tool, "params": {
        "e2_node_id": e2_node_id,
        "dl_slice_id": dl_slice_id, "dl_pos_low": dl_pos_low, "dl_pos_high": dl_pos_high,
        "ul_slice_id": ul_slice_id, "ul_pos_low": ul_pos_low, "ul_pos_high": ul_pos_high,
        "dry_run": dry_run,
    }}

    try:
        if not CONTROL_ENABLED:
            raise PolicyError("control_disabled by server policy")

        enforce_allowlist(e2_node_id)
        validate_prb_range(dl_pos_low, dl_pos_high)
        validate_prb_range(ul_pos_low, ul_pos_high)

        enforce_rate_limit(tool)

        payload = {
            "e2_node_id": e2_node_id,
            "dl_slice_id": dl_slice_id, "dl_pos_low": dl_pos_low, "dl_pos_high": dl_pos_high,
            "ul_slice_id": ul_slice_id, "ul_pos_low": ul_pos_low, "ul_pos_high": ul_pos_high,
        }

        dr = maybe_dry_run(tool, payload, dry_run)
        if dr:
            event.update({"ok": True, "dry_run": True})
            audit_log(event)
            return dr

        res = _post("/slice/control/static", payload)
        event.update({"ok": True, "result": {"ans": res.get("ans"), "diagnostic": res.get("diagnostic")}})
        audit_log(event)
        return res

    except PolicyError as pe:
        event.update({"ok": False, "denied": True, "reason": str(pe)})
        audit_log(event)
        return {"ok": False, "denied": True, "reason": str(pe)}
    except Exception as e:
        event.update({"ok": False, "error": str(e)})
        audit_log(event)
        raise

if __name__ == "__main__":
    mcp.run()
