"""Cisco ACI MCP server — health monitoring tools for ACI fabric."""

import os
import json
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

from .aci_client import ACIClient

app = Server("cisco-aci-health")

# Client is initialised lazily on first tool call via _get_client().
_client: ACIClient | None = None


def _get_client() -> ACIClient:
    global _client
    if _client is not None:
        return _client

    host = os.environ.get("ACI_HOST", "")
    username = os.environ.get("ACI_USERNAME", "")
    password = os.environ.get("ACI_PASSWORD", "")
    verify_ssl = os.environ.get("ACI_VERIFY_SSL", "true").lower() != "false"

    if not host or not username or not password:
        raise RuntimeError(
            "ACI_HOST, ACI_USERNAME, ACI_PASSWORD environment variables are required."
        )

    _client = ACIClient(host, username, password, verify_ssl)
    _client.login()
    return _client


def _ok(data: Any) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


def _err(msg: str) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"ERROR: {msg}")]


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    types.Tool(
        name="get_fabric_health",
        description=(
            "ACIファブリック全体のヘルススコアを取得します。"
            "スコアは0-100の範囲で、100が最も健全です。"
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="get_pod_health",
        description="各ポッドのヘルス状態を取得します。",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="get_node_list",
        description=(
            "ACI ファブリック内のすべてのノード（Spine/Leaf/APIC）の一覧と"
            "ヘルススコアを取得します。"
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="get_node_health",
        description="指定したノードの詳細なヘルス情報を取得します。",
        inputSchema={
            "type": "object",
            "properties": {
                "pod_id": {
                    "type": "integer",
                    "description": "ポッドID（通常は1）",
                    "default": 1,
                },
                "node_id": {
                    "type": "integer",
                    "description": "ノードID（例: 101, 102, 201, 202）",
                },
            },
            "required": ["node_id"],
        },
    ),
    types.Tool(
        name="get_fault_summary",
        description=(
            "アクティブなフォルト（障害）のサマリーを重大度別に取得します。"
            "critical / major / minor / warning の件数を確認できます。"
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="get_faults",
        description="アクティブなフォルトの詳細一覧を取得します。",
        inputSchema={
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "description": "フィルタする重大度: critical / major / minor / warning / cleared",
                    "enum": ["critical", "major", "minor", "warning", "cleared"],
                },
                "limit": {
                    "type": "integer",
                    "description": "最大取得件数（デフォルト: 50）",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 200,
                },
            },
            "required": [],
        },
    ),
    types.Tool(
        name="get_tenant_health",
        description="テナントごとのヘルススコアを取得します。",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="get_system_info",
        description=(
            "各ノードのシステム情報（ロール・状態・アップタイム・IPアドレス）を取得します。"
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="get_apic_health",
        description="APIC コントローラ自体のヘルス状態を取得します。",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def _format_fabric_health(raw: list[dict]) -> list[dict]:
    out = []
    for item in raw:
        attrs = item.get("fabricHealthTotal", {}).get("attributes", {})
        out.append({
            "dn": attrs.get("dn"),
            "health_score": int(attrs.get("cur", 0)),
            "previous_score": int(attrs.get("prev", 0)),
        })
    return out


def _format_node_list(raw: list[dict]) -> list[dict]:
    out = []
    for item in raw:
        attrs = item.get("fabricNode", {}).get("attributes", {})
        children = item.get("fabricNode", {}).get("children", [])
        health = None
        for child in children:
            if "healthInst" in child:
                health = int(child["healthInst"]["attributes"].get("cur", 0))
        out.append({
            "node_id": attrs.get("id"),
            "name": attrs.get("name"),
            "role": attrs.get("role"),
            "state": attrs.get("fabricSt"),
            "model": attrs.get("model"),
            "serial": attrs.get("serial"),
            "address": attrs.get("address"),
            "health_score": health,
        })
    return out


def _format_fault_summary(raw: list[dict]) -> list[dict]:
    out = []
    for item in raw:
        attrs = item.get("faultSummary", {}).get("attributes", {})
        out.append({
            "code": attrs.get("code"),
            "severity": attrs.get("severity"),
            "count": int(attrs.get("count", 0)),
            "cause": attrs.get("cause"),
            "description": attrs.get("descr"),
            "domain": attrs.get("domain"),
            "type": attrs.get("type"),
        })
    return out


def _format_faults(raw: list[dict]) -> list[dict]:
    out = []
    for item in raw:
        attrs = item.get("faultInst", {}).get("attributes", {})
        out.append({
            "code": attrs.get("code"),
            "severity": attrs.get("severity"),
            "dn": attrs.get("dn"),
            "description": attrs.get("descr"),
            "cause": attrs.get("cause"),
            "created": attrs.get("created"),
            "last_transition": attrs.get("lastTransition"),
            "lc": attrs.get("lc"),
            "rule": attrs.get("rule"),
        })
    return out


def _format_tenant_health(raw: list[dict]) -> list[dict]:
    out = []
    for item in raw:
        attrs = item.get("fvTenant", {}).get("attributes", {})
        children = item.get("fvTenant", {}).get("children", [])
        health = None
        for child in children:
            if "healthInst" in child:
                health = int(child["healthInst"]["attributes"].get("cur", 0))
        out.append({
            "name": attrs.get("name"),
            "dn": attrs.get("dn"),
            "description": attrs.get("descr"),
            "health_score": health,
        })
    return out


def _format_system_info(raw: list[dict]) -> list[dict]:
    out = []
    for item in raw:
        attrs = item.get("topSystem", {}).get("attributes", {})
        out.append({
            "node_id": attrs.get("id"),
            "name": attrs.get("name"),
            "role": attrs.get("role"),
            "state": attrs.get("state"),
            "address": attrs.get("address"),
            "oob_mgmt_addr": attrs.get("oobMgmt"),
            "pod_id": attrs.get("podId"),
            "system_uptime": attrs.get("systemUpTime"),
            "current_time": attrs.get("currentTime"),
            "version": attrs.get("version"),
        })
    return out


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        client = _get_client()

        if name == "get_fabric_health":
            raw = client.get_fabric_health()
            data = _format_fabric_health(raw)
            if data:
                score = data[0]["health_score"]
                status = "健全" if score >= 90 else "注意" if score >= 70 else "警告"
                return _ok({"status": status, "results": data})
            return _ok({"status": "データなし", "results": []})

        elif name == "get_pod_health":
            raw = client.get_pod_health()
            return _ok(raw)

        elif name == "get_node_list":
            raw = client.get_node_list()
            data = _format_node_list(raw)
            summary = {
                "total": len(data),
                "active": sum(1 for n in data if n["state"] == "active"),
                "inactive": sum(1 for n in data if n["state"] != "active"),
                "nodes": data,
            }
            return _ok(summary)

        elif name == "get_node_health":
            pod_id = arguments.get("pod_id", 1)
            node_id = arguments["node_id"]
            raw = client.get_node_health(pod_id, node_id)
            return _ok(raw)

        elif name == "get_fault_summary":
            raw = client.get_fault_summary()
            data = _format_fault_summary(raw)
            counts: dict[str, int] = {}
            for f in data:
                sev = f["severity"]
                counts[sev] = counts.get(sev, 0) + f["count"]
            return _ok({"severity_counts": counts, "faults": data})

        elif name == "get_faults":
            severity = arguments.get("severity")
            limit = arguments.get("limit", 50)
            raw = client.get_faults(severity=severity, limit=limit)
            data = _format_faults(raw)
            return _ok({"total_returned": len(data), "faults": data})

        elif name == "get_tenant_health":
            raw = client.get_tenant_health()
            data = _format_tenant_health(raw)
            return _ok({"total_tenants": len(data), "tenants": data})

        elif name == "get_system_info":
            raw = client.get_system_info()
            data = _format_system_info(raw)
            return _ok({"total_nodes": len(data), "nodes": data})

        elif name == "get_apic_health":
            raw = client.get_apic_health()
            return _ok(raw)

        else:
            return _err(f"Unknown tool: {name}")

    except RuntimeError as e:
        return _err(str(e))
    except Exception as e:
        return _err(f"Unexpected error: {e}")


async def main() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
