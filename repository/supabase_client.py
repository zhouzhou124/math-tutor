"""Lightweight Supabase REST API client using httpx — no dependency needed."""
import json
import httpx
from typing import Optional, List, Dict, Any


class SupabaseClient:
    """Minimal Supabase client via REST API. Uses httpx (already in project)."""

    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _request(self, method: str, path: str, data: dict = None,
                 params: dict = None) -> httpx.Response:
        url = f"{self.url}/rest/v1{path}"
        r = httpx.request(
            method, url, headers=self._headers, json=data, params=params, timeout=15
        )
        if r.status_code >= 400:
            raise RuntimeError(f"Supabase {method} {path} failed: {r.status_code} {r.text[:200]}")
        return r

    def select(self, table: str, columns: str = "*", filters: dict = None,
               order: str = None, limit: int = None) -> List[Dict]:
        params = {"select": columns}
        if filters:
            for k, v in filters.items():
                params[k] = f"eq.{v}" if not str(k).startswith("like") else v
        if order:
            params["order"] = order
        if limit:
            params["limit"] = limit
        r = self._request("GET", f"/{table}", params=params)
        return r.json() if r.text else []

    def insert(self, table: str, data: dict) -> Dict:
        r = self._request("POST", f"/{table}", data=data)
        rows = r.json()
        return rows[0] if rows else {}

    def update(self, table: str, data: dict, filters: dict) -> List[Dict]:
        params = {}
        for k, v in filters.items():
            params[k] = f"eq.{v}"
        r = self._request("PATCH", f"/{table}", data=data, params=params)
        return r.json() if r.text else []

    def delete(self, table: str, filters: dict) -> List[Dict]:
        params = {}
        for k, v in filters.items():
            params[k] = f"eq.{v}"
        r = self._request("DELETE", f"/{table}", params=params)
        return r.json() if r.text else []

    def rpc(self, fn: str, params: dict = None) -> Any:
        r = self._request("POST", f"/rpc/{fn}", data=params or {})
        return r.json() if r.text else None
