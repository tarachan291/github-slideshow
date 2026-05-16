"""Cisco APIC REST API client."""

import ssl
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Any


class ACIClient:
    def __init__(self, host: str, username: str, password: str, verify_ssl: bool = True):
        self.base_url = f"https://{host}"
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.token: str | None = None
        self._ssl_context = ssl.create_default_context() if verify_ssl else self._insecure_context()

    @staticmethod
    def _insecure_context() -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Cookie"] = f"APIC-Cookie={self.token}"

        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, context=self._ssl_context, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"APIC API error {e.code}: {e.read().decode()}") from e

    def login(self) -> None:
        payload = {"aaaUser": {"attributes": {"name": self.username, "pwd": self.password}}}
        resp = self._request("POST", "/api/aaaLogin.json", payload)
        self.token = resp["imdata"][0]["aaaLogin"]["attributes"]["token"]

    def get(self, path: str) -> list[dict]:
        resp = self._request("GET", path)
        return resp.get("imdata", [])

    # ---- Health ----

    def get_fabric_health(self) -> list[dict]:
        return self.get("/api/node/class/fabricHealthTotal.json")

    def get_pod_health(self) -> list[dict]:
        return self.get(
            "/api/node/class/fabricPod.json?rsp-subtree-include=health,no-scoped"
        )

    def get_node_list(self) -> list[dict]:
        return self.get(
            "/api/node/class/fabricNode.json"
            "?rsp-subtree-include=health,no-scoped"
            "&order-by=fabricNode.id"
        )

    def get_node_health(self, pod_id: int, node_id: int) -> list[dict]:
        dn = f"topology/pod-{pod_id}/node-{node_id}"
        return self.get(
            f"/api/node/mo/{dn}.json?rsp-subtree-include=health,no-scoped"
        )

    # ---- Faults ----

    def get_fault_summary(self) -> list[dict]:
        return self.get("/api/node/class/faultSummary.json?order-by=faultSummary.severity|desc")

    def get_faults(
        self,
        severity: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        query = f"/api/node/class/faultInst.json?page-size={limit}&order-by=faultInst.severity|desc"
        if severity:
            query += f"&query-target-filter=eq(faultInst.severity,\"{severity}\")"
        return self.get(query)

    # ---- Tenants ----

    def get_tenant_health(self) -> list[dict]:
        return self.get(
            "/api/node/class/fvTenant.json?rsp-subtree-include=health,no-scoped"
        )

    # ---- System ----

    def get_system_info(self) -> list[dict]:
        return self.get("/api/node/class/topSystem.json?order-by=topSystem.id")

    def get_apic_health(self) -> list[dict]:
        return self.get(
            "/api/node/class/infraCont.json?rsp-subtree-include=health,no-scoped"
        )
