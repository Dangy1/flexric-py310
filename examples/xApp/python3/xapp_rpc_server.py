# xapp_rpc_server.py
import json
import os
import time
import threading
from contextlib import asynccontextmanager
from typing import Any, Dict, List
from collections import deque

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

import xapp_sdk  # your SWIG wrapper module

load_dotenv()

# ----------------------------
# Env / security knobs
# ----------------------------
def _env_str(name: str, default: str = "") -> str:
    v = os.getenv(name, default)
    return v.strip()

def _env_int(name: str, default: int) -> int:
    v = os.getenv(name, "").strip()
    if v == "":
        return default
    try:
        return int(v)
    except Exception:
        return default

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name, "").strip().lower()
    if v == "":
        return default
    return v in ("1", "true", "yes", "y", "on")

E2_NODE_ALLOWLIST = [s.strip() for s in _env_str("E2_NODE_ALLOWLIST", "").split(",") if s.strip()]
RATE_LIMIT_RPS = _env_int("RATE_LIMIT_RPS", 0)  # 0 disables
DRY_RUN = _env_bool("DRY_RUN", False)
PRB_MAX_LOW = _env_int("PRB_MAX_LOW", 0)
PRB_MAX_HIGH = _env_int("PRB_MAX_HIGH", 273)
AUDIT_LOG_PATH = _env_str("AUDIT_LOG_PATH", "/tmp/xapp_rpc_audit.log")

# ----------------------------
# Global state
# ----------------------------
_started = False
_state_lock = threading.Lock()

# sub_id -> deque[dict]
_ind_queues: Dict[str, deque] = {}
# sub_id -> opaque handle
_sub_handles: Dict[str, Any] = {}
# sub_id -> metadata
_sub_meta: Dict[str, Dict[str, Any]] = {}

def _now_ms() -> int:
    return int(time.time() * 1000)

# ----------------------------
# Rate limiter (simple global token bucket)
# ----------------------------
_rl_lock = threading.Lock()
_rl_tokens = 0.0
_rl_last = time.time()

def _rate_limit_check() -> None:
    global _rl_tokens, _rl_last
    if RATE_LIMIT_RPS <= 0:
        return

    with _rl_lock:
        now = time.time()
        elapsed = now - _rl_last
        _rl_last = now

        # refill
        _rl_tokens = min(float(RATE_LIMIT_RPS), _rl_tokens + elapsed * float(RATE_LIMIT_RPS))

        # spend
        if _rl_tokens >= 1.0:
            _rl_tokens -= 1.0
            return

    raise HTTPException(status_code=429, detail="rate_limited")

# ----------------------------
# Audit log
# ----------------------------
_audit_lock = threading.Lock()

def _audit(event: str, params: Dict[str, Any], request: Request | None = None) -> None:
    rec = {
        "ts_ms": _now_ms(),
        "event": event,
        "params": params,
    }
    if request is not None:
        rec["client"] = getattr(request.client, "host", None)
        rec["path"] = request.url.path

    line = json.dumps(rec, ensure_ascii=False)
    try:
        with _audit_lock:
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        # don't crash the server due to logging issues
        pass

# ----------------------------
# SWIG-safe serialization helpers
# ----------------------------
def _safe_scalar(x: Any) -> Any:
    """Convert SWIG/unknown objects to JSON-safe scalar."""
    if x is None:
        return None
    if isinstance(x, (str, int, float, bool)):
        return x

    # common SWIG patterns: try str()/int() safely
    try:
        s = str(x)
        # If it's like "<Swig Object of type '...'>", still okay to expose as string
        return s
    except Exception:
        pass

    try:
        return int(x)
    except Exception:
        pass

    # last resort
    return repr(x)

def _safe_list(x: Any, max_items: int = 256) -> List[Any]:
    """Try to iterate; if not possible, return [stringified]."""
    if x is None:
        return []
    if isinstance(x, list):
        return [_safe_scalar(i) for i in x[:max_items]]
    if isinstance(x, tuple):
        return [_safe_scalar(i) for i in x[:max_items]]

    # SWIG vectors sometimes support __len__/__getitem__
    try:
        n = len(x)  # type: ignore[arg-type]
        out = []
        for i in range(min(n, max_items)):
            out.append(_safe_scalar(x[i]))  # type: ignore[index]
        return out
    except Exception:
        pass

    # try generic iteration
    try:
        out = []
        for i, v in enumerate(x):
            if i >= max_items:
                break
            out.append(_safe_scalar(v))
        return out
    except Exception:
        return [_safe_scalar(x)]

def _normalize_node_id(node_id: Any) -> str:
    # always return a string id for allowlist checks + JSON
    return str(_safe_scalar(node_id))

def _allowlisted(e2_node_id: str) -> bool:
    if not E2_NODE_ALLOWLIST:
        return True
    return e2_node_id in E2_NODE_ALLOWLIST

# ----------------------------
# FlexRIC lifecycle
# ----------------------------
def ensure_started():
    global _started
    with _state_lock:
        if _started:
            return
        xapp_sdk.init()
        _started = True

def stop_everything():
    global _started
    # best effort cleanup
    try:
        for sub_id, h in list(_sub_handles.items()):
            try:
                xapp_sdk.rm_report_slice_sm(h)
            except Exception:
                pass
        _sub_handles.clear()
        _ind_queues.clear()
        _sub_meta.clear()
        try:
            xapp_sdk.try_stop()
        except Exception:
            pass
    finally:
        _started = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start lazily (keep init explicit on first request) OR init here.
    # If you want auto-init on server start, uncomment ensure_started():
    # ensure_started()
    yield
    stop_everything()

app = FastAPI(title="FlexRIC xApp RPC", lifespan=lifespan)

# ----------------------------
# Helpers: E2 node listing
# ----------------------------
def list_e2_nodes_safe() -> List[Dict[str, Any]]:
    nodes = xapp_sdk.conn_e2_nodes()  # SWIG type
    out: List[Dict[str, Any]] = []

    # Try SWIG vector semantics
    try:
        n = len(nodes)  # type: ignore[arg-type]
        for i in range(n):
            node = nodes[i]  # type: ignore[index]
            node_id = _normalize_node_id(getattr(node, "id", None))
            ran_func = getattr(node, "ran_func", None)

            out.append(
                {
                    "id": node_id,
                    "ran_func": _safe_list(ran_func),
                }
            )
        return out
    except Exception:
        pass

    # Fallback generic iteration
    try:
        for node in nodes:
            node_id = _normalize_node_id(getattr(node, "id", None))
            ran_func = getattr(node, "ran_func", None)
            out.append({"id": node_id, "ran_func": _safe_list(ran_func)})
        return out
    except Exception:
        # last resort: stringify whatever came back
        return [{"id": "unknown", "ran_func": [], "raw": _safe_scalar(nodes)}]

# ----------------------------
# Slice callback: cache indications
# ----------------------------
class SliceIndicationHandler(xapp_sdk.slice_cb):
    def __init__(self, sub_id: str, maxlen: int = 2000):
        super().__init__()
        self.sub_id = sub_id
        self.maxlen = maxlen

    def handle(self, ind_msg):
        try:
            ts = getattr(ind_msg, "tstamp", None)
            payload = {
                "sub_id": self.sub_id,
                "rx_ts_ms": _now_ms(),
                "tstamp": _safe_scalar(ts),
            }
        except Exception as e:
            payload = {"sub_id": self.sub_id, "rx_ts_ms": _now_ms(), "error": str(e)}

        q = _ind_queues.get(self.sub_id)
        if q is not None:
            q.append(payload)

# ----------------------------
# RPC models
# ----------------------------
class SubscribeReq(BaseModel):
    e2_node_id: str
    interval_ms: int
    queue_maxlen: int

class PollReq(BaseModel):
    sub_id: str
    max_items: int

class UnsubscribeReq(BaseModel):
    sub_id: str

class SliceStaticReq(BaseModel):
    e2_node_id: str
    dl_slice_id: int
    dl_pos_low: int
    dl_pos_high: int
    ul_slice_id: int
    ul_pos_low: int
    ul_pos_high: int

# ----------------------------
# Middleware-ish checks per endpoint
# ----------------------------
def _precheck(request: Request, e2_node_id: str | None = None) -> None:
    _rate_limit_check()
    if e2_node_id is not None:
        if not _allowlisted(e2_node_id):
            _audit("deny_allowlist", {"e2_node_id": e2_node_id}, request)
            raise HTTPException(status_code=403, detail="e2_node_id_not_allowlisted")

# ----------------------------
# Endpoints
# ----------------------------
@app.get("/health")
def health(request: Request):
    _precheck(request)
    _audit("health", {"started": _started}, request)
    return {
        "ok": True,
        "ts_ms": _now_ms(),
        "started": _started,
        "detail": "RPC process is alive. Use /ready or a functional endpoint to force xApp initialization.",
    }

@app.get("/ready")
def ready(request: Request):
    _precheck(request)
    ensure_started()
    nodes = list_e2_nodes_safe()
    _audit("ready", {"started": _started, "node_count": len(nodes)}, request)
    return {
        "ok": True,
        "ts_ms": _now_ms(),
        "started": _started,
        "node_count": len(nodes),
    }

@app.get("/e2/nodes")
def e2_nodes(request: Request):
    _precheck(request)
    ensure_started()
    nodes = list_e2_nodes_safe()

    # apply allowlist filter (if set)
    if E2_NODE_ALLOWLIST:
        nodes = [n for n in nodes if n.get("id") in E2_NODE_ALLOWLIST]

    _audit("e2_nodes", {"count": len(nodes)}, request)
    return {"nodes": nodes}

@app.get("/debug/e2/nodes_raw")
def debug_e2_nodes_raw(request: Request):
    """Debug only: show raw stringified output to understand SWIG fields."""
    _precheck(request)
    ensure_started()
    raw = xapp_sdk.conn_e2_nodes()
    _audit("debug_e2_nodes_raw", {}, request)
    return {"raw": _safe_scalar(raw)}

@app.post("/slice/subscribe")
def slice_subscribe(req: SubscribeReq, request: Request):
    _precheck(request, req.e2_node_id)
    ensure_started()

    sub_id = f"slice-{req.e2_node_id}-{_now_ms()}"
    _ind_queues[sub_id] = deque(maxlen=req.queue_maxlen)
    handler = SliceIndicationHandler(sub_id=sub_id, maxlen=req.queue_maxlen)

    if req.interval_ms <= 1:
        inter = xapp_sdk.Interval_ms_1
    elif req.interval_ms <= 2:
        inter = xapp_sdk.Interval_ms_2
    elif req.interval_ms <= 5:
        inter = xapp_sdk.Interval_ms_5
    else:
        inter = xapp_sdk.Interval_ms_10

    _audit("slice_subscribe", req.model_dump(), request)

    try:
        h = xapp_sdk.report_slice_sm(req.e2_node_id, inter, handler)
    except Exception as e:
        _ind_queues.pop(sub_id, None)
        raise HTTPException(status_code=500, detail=f"report_slice_sm failed: {e}")

    _sub_handles[sub_id] = h
    _sub_meta[sub_id] = {
        "e2_node_id": req.e2_node_id,
        "interval_ms": req.interval_ms,
        "created_ms": _now_ms(),
    }
    return {"sub_id": sub_id, "meta": _sub_meta[sub_id]}

@app.post("/slice/poll")
def slice_poll(req: PollReq, request: Request):
    _precheck(request)
    ensure_started()

    q = _ind_queues.get(req.sub_id)
    if q is None:
        raise HTTPException(status_code=404, detail="unknown_sub_id")

    items = []
    for _ in range(min(req.max_items, len(q))):
        items.append(q.popleft())

    _audit("slice_poll", {"sub_id": req.sub_id, "returned": len(items), "remaining": len(q)}, request)
    return {"sub_id": req.sub_id, "items": items, "remaining": len(q)}

@app.post("/slice/unsubscribe")
def slice_unsubscribe(req: UnsubscribeReq, request: Request):
    _precheck(request)
    ensure_started()

    _audit("slice_unsubscribe", {"sub_id": req.sub_id}, request)

    h = _sub_handles.pop(req.sub_id, None)
    _ind_queues.pop(req.sub_id, None)
    _sub_meta.pop(req.sub_id, None)

    if h is None:
        return {"ok": True, "detail": "already_removed"}

    try:
        xapp_sdk.rm_report_slice_sm(h)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"rm_report_slice_sm failed: {e}")

    return {"ok": True}

@app.post("/slice/control/static")
def slice_control_static(req: SliceStaticReq, request: Request):
    _precheck(request, req.e2_node_id)
    ensure_started()

    # bounds check
    for vname in ("dl_pos_low", "dl_pos_high", "ul_pos_low", "ul_pos_high"):
        v = getattr(req, vname)
        if v < PRB_MAX_LOW or v > PRB_MAX_HIGH:
            raise HTTPException(status_code=400, detail=f"{vname}_out_of_range")

    if req.dl_pos_low > req.dl_pos_high or req.ul_pos_low > req.ul_pos_high:
        raise HTTPException(status_code=400, detail="pos_low_gt_pos_high")

    # audit first
    _audit("slice_control_static", {**req.model_dump(), "dry_run": DRY_RUN}, request)

    if DRY_RUN:
        return {"ok": True, "dry_run": True}

    try:
        ctrl = xapp_sdk.slice_ctrl_msg_t()
        ctrl.type = xapp_sdk.SLICE_CTRL_SM_V0_ADD  # adjust if your SM uses MODIFY etc.

        add = ctrl.u.add_mod_slice

        # DL
        dl_conf = add.dl
        dl_conf.len_sched_name = 0
        dl_conf.sched_name = ""
        dl_conf.len_slices = 1
        dl_conf.slices = xapp_sdk.slice_array(1)
        dl_slice = dl_conf.slices[0]
        dl_slice.id = req.dl_slice_id
        dl_slice.len_label = 0
        dl_slice.label = ""
        dl_slice.len_sched = 0
        dl_slice.sched = ""
        dl_slice.params = xapp_sdk.slice_params_t()
        dl_slice.params.type = xapp_sdk.SLICE_ALG_SM_V0_STATIC
        dl_slice.params.u.sta = xapp_sdk.static_slice_t()
        dl_slice.params.u.sta.pos_low = req.dl_pos_low
        dl_slice.params.u.sta.pos_high = req.dl_pos_high

        # UL
        ul_conf = add.ul
        ul_conf.len_sched_name = 0
        ul_conf.sched_name = ""
        ul_conf.len_slices = 1
        ul_conf.slices = xapp_sdk.slice_array(1)
        ul_slice = ul_conf.slices[0]
        ul_slice.id = req.ul_slice_id
        ul_slice.len_label = 0
        ul_slice.label = ""
        ul_slice.len_sched = 0
        ul_slice.sched = ""
        ul_slice.params = xapp_sdk.slice_params_t()
        ul_slice.params.type = xapp_sdk.SLICE_ALG_SM_V0_STATIC
        ul_slice.params.u.sta = xapp_sdk.static_slice_t()
        ul_slice.params.u.sta.pos_low = req.ul_pos_low
        ul_slice.params.u.sta.pos_high = req.ul_pos_high

        out = xapp_sdk.control_slice_sm(req.e2_node_id, ctrl)

        return {
            "ok": True,
            "ans": _safe_scalar(getattr(out, "ans", None)),
            "diagnostic": _safe_scalar(getattr(out, "diagnostic", None)),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"control_slice_sm failed: {e}")
