#!/usr/bin/env python3
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from flexric_client import FlexRICClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flexric-mcp")

mcp = FastMCP("flexric-mcp-server")  # <-- IMPORTANT: global FastMCP object

flexric_client: Optional[FlexRICClient] = None


@mcp.tool()
async def list_e2_nodes() -> Dict[str, Any]:
    """List all connected E2 nodes (base stations) and their status."""
    if flexric_client is None:
        return {"status": "error", "error": "FlexRIC client not initialized"}
    nodes = await flexric_client.list_e2_nodes()
    return {"status": "success", "result": nodes, "timestamp": datetime.now().isoformat()}


@mcp.tool()
async def get_kpi_metrics(e2_node_id: Optional[str] = None,
                          metric_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """Retrieve KPIs (throughput, latency, PRB util, connected UEs, etc.)."""
    if flexric_client is None:
        return {"status": "error", "error": "FlexRIC client not initialized"}
    res = await flexric_client.get_kpi_metrics(e2_node_id=e2_node_id, metric_types=metric_types)
    return {"status": "success", "result": res, "timestamp": datetime.now().isoformat()}


@mcp.tool()
async def get_slice_metrics(e2_node_id: str, slice_id: Optional[int] = None) -> Dict[str, Any]:
    """Get slice-specific metrics/config for an E2 node."""
    if flexric_client is None:
        return {"status": "error", "error": "FlexRIC client not initialized"}
    res = await flexric_client.get_slice_metrics(e2_node_id=e2_node_id, slice_id=slice_id)
    return {"status": "success", "result": res, "timestamp": datetime.now().isoformat()}


@mcp.tool()
async def get_ue_metrics(e2_node_id: str, rnti: Optional[int] = None) -> Dict[str, Any]:
    """Get per-UE metrics (CQI/RSRP/throughput/buffer)."""
    if flexric_client is None:
        return {"status": "error", "error": "FlexRIC client not initialized"}
    res = await flexric_client.get_ue_metrics(e2_node_id=e2_node_id, rnti=rnti)
    return {"status": "success", "result": res, "timestamp": datetime.now().isoformat()}


@mcp.tool()
async def send_rc_control(e2_node_id: str,
                          control_type: str,
                          parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Send RC control commands (slice_config, ue_priority, handover, prb_allocation)."""
    if flexric_client is None:
        return {"status": "error", "error": "FlexRIC client not initialized"}
    res = await flexric_client.send_rc_control(
        e2_node_id=e2_node_id,
        control_type=control_type,
        parameters=parameters,
    )
    return {"status": "success", "result": res, "timestamp": datetime.now().isoformat()}


@mcp.tool()
async def configure_slice(e2_node_id: str,
                          slice_id: int,
                          prb_quota: Optional[float] = None,
                          scheduler: Optional[str] = None,
                          priority: Optional[int] = None) -> Dict[str, Any]:
    """Configure slice PRB quota/scheduler/priority."""
    if flexric_client is None:
        return {"status": "error", "error": "FlexRIC client not initialized"}
    res = await flexric_client.configure_slice(
        e2_node_id=e2_node_id,
        slice_id=slice_id,
        prb_quota=prb_quota,
        scheduler=scheduler,
        priority=priority,
    )
    return {"status": "success", "result": res, "timestamp": datetime.now().isoformat()}


@mcp.tool()
async def get_cell_metrics(e2_node_id: str, cell_id: Optional[int] = None) -> Dict[str, Any]:
    """Get cell-level metrics."""
    if flexric_client is None:
        return {"status": "error", "error": "FlexRIC client not initialized"}
    res = await flexric_client.get_cell_metrics(e2_node_id=e2_node_id, cell_id=cell_id)
    return {"status": "success", "result": res, "timestamp": datetime.now().isoformat()}


@mcp.tool()
async def trigger_handover(e2_node_id: str, rnti: int, target_cell_id: int) -> Dict[str, Any]:
    """Trigger UE handover to target cell."""
    if flexric_client is None:
        return {"status": "error", "error": "FlexRIC client not initialized"}
    res = await flexric_client.trigger_handover(
        e2_node_id=e2_node_id, rnti=rnti, target_cell_id=target_cell_id
    )
    return {"status": "success", "result": res, "timestamp": datetime.now().isoformat()}


def init_flexric():
    """Init client once at import time (so mcp dev sees ready server)."""
    global flexric_client
    try:
        flexric_client = FlexRICClient(near_ric_ip="127.0.0.1", near_ric_port=36421)
        # If connect() is async, do it lazily inside tools OR convert to sync connect.
        # Easiest: keep connect inside tool calls or create a background task elsewhere.
        logger.info("FlexRIC client object created")
    except Exception as e:
        logger.error(f"Failed to create FlexRIC client: {e}")
        flexric_client = None


init_flexric()