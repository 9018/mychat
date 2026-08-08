#!/usr/bin/env python3
"""Verify the self-hosted xAI-compatible gateway is reachable and working."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from lib import xai_compat as xc
except ImportError:
    from lib import xai_compat as xc
print("XAI_BASE      =", xc.api_base())
print("UPSTREAM_PROXY =", os.environ.get("UPSTREAM_PROXY") or "(none)")
print("XAI_API_KEY    =", ("set" if os.environ.get("XAI_API_KEY") or os.environ.get("GROK2API_KEY") else "MISSING"))
import requests
r = requests.get(xc.api_base() + "/v1/models", headers={
    "Authorization": "Bearer " + (os.environ.get("XAI_API_KEY") or os.environ.get("GROK2API_KEY"))},
    proxies=xc.proxies(), timeout=30)
print("GET /v1/models ->", r.status_code, "| models:", len(r.json().get("data", [])))
