#!/usr/bin/env python3
import asyncio
import json
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

# FlexRIC python SDK (SWIG)
# Your build provides either xapp_sdk.py (wrapper) or only _xapp_sdk.so
try:
    import xapp_sdk as sdk
except Exception:
    import _xapp_sdk as sdk  # fallback


mcp = FastMCP("flexric-kpm-rc")

# ----------------------------
# Shared state
# ----------------------------
LATEST_KPM: Dict[str, Any] = {"status": "empty", "ts": None, "data": None}
SDK_STARTED = False
SDK_LOCK = threading.Lock()

# If SDK is blocking (very common), we run it in a background thread.
SDK_THREAD: Optional[threading.Thread] = None


# ----------------------------
# 1) YOU ONLY NEED TO EDIT THIS SECTION
#    Wire these functions using FlexRIC's existing python examples:
#    - examples/xApp/python3/xapp_kpm_*.py
#    - examples/xApp/python3/xapp_*rc*.py
# ----------------------------

def _sdk_start_and_subscribe_kpm():
    """
    Start xApp runtime + subscribe KPM.
    This usually blocks inside the SDK event loop, so run it in a thread.
    """
    # ---- IMPORTANT ----
    # Replace the lines below with the actual init/start/subscribe calls
    # you see in FlexRIC's python example scripts.
    #
    # Typical flow in FlexRIC examples is:
    #   sdk.init(...) or sdk.xapp_init(...)
    #   sdk.conn_e2_nodes / wait for nodes
    #   sdk.subscribe_kpm(..., callback)
    #   sdk.run()  (blocking loop)
    #
    # You must adapt names to your SDK.
    # -------------------

    def on_kpm_indication(ind: Any):
        # Convert 'ind' to python dict/string depending on SDK type
        # In examples they often provide a helper to decode/print.
        global LATEST_KPM
        try:
            payload = _kpm_to_dict(ind)
        except Exception:
            payload = {"raw": str(ind)}
        LATEST_KPM = {
            "status": "ok",
            "ts": datetime.now().isoformat(),
            "data": payload,
        }

    # ---- PLACEHOLDERS: REPLACE WITH REAL SDK CALLS ----
    # Example pseudo-calls (NOT real):
    # sdk.xapp_init()
    # sdk.kpm_subscribe(callback=on_kpm_indication, interval_ms=1000)
    # sdk.xapp_run_forever()
    #
    # If you don’t know what calls exist: open FlexRIC python examples and copy.
    raise RuntimeError(
        "SDK wiring not implemented yet. Copy init/subscribe/run logic from FlexRIC python examples "
        "(xapp_kpm_*.py and xapp_*rc*.py) and replace the placeholder section."
    )


def _kpm_to_dict(ind: Any) -> Dict[str, Any]:
    """
    Optional: decode the KPM indication into a dict.
    Replace with the decode helper from your example script.
    """
    return {"raw": str(ind)}


def _sdk_send_rc(e2_node_id: str, rc_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send one RC control command via SDK.
    Implement using the RC python example.
    """
    # ---- PLACEHOLDERS: REPLACE WITH REAL SDK CALLS ----
    # Example pseudo-calls (NOT real):
    # sdk.rc_control(e2_node_id, rc_payload)
    return {
        "status": "ok",
        "applied": True,
        "e2_node_id": e2_node_id,
        "payload": rc_payload,
    }


# ----------------------------
# SDK bootstrap (lazy)
# ----------------------------
def _ensure_sdk_running():
    global SDK_STARTED, SDK_THREAD
    with SDK_LOCK:
        if SDK_STARTED:
            return
        SDK_STARTED = True

        def runner():
            try:
                _sdk_start_and_subscribe_kpm()
            except Exception as e:
                # store error into LATEST_KPM so MCP tool shows it
                global LATEST_KPM
                LATEST_KPM = {"status": "error", "ts": datetime.now().isoformat(), "error": str(e)}

        SDK_THREAD = threading.Thread(target=runner, daemon=True)
        SDK_THREAD.start()


# ----------------------------
# MCP tools
# ----------------------------
@mcp.tool()
async def kpm_latest() -> Dict[str, Any]:
    """Return latest KPM metrics snapshot (from memory)."""
    _ensure_sdk_running()
    return {"status": "success", "result": LATEST_KPM, "now": datetime.now().isoformat()}


@mcp.tool()
async def rc_command(e2_node_id: str, rc_json: str) -> Dict[str, Any]:
    """
    Send one RC command.
    rc_json should be a JSON string that your RC example expects (or that you translate inside _sdk_send_rc()).
    """
    _ensure_sdk_running()
    try:
        payload = json.loads(rc_json) if rc_json else {}
        if not isinstance(payload, dict):
            raise ValueError("rc_json must decode to a JSON object")
    except Exception as e:
        return {"status": "error", "error": f"bad rc_json: {e}"}

    res = await asyncio.to_thread(_sdk_send_rc, e2_node_id, payload)
    return {"status": "success", "result": res, "now": datetime.now().isoformat()}