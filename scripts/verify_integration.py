#!/usr/bin/env python3
"""Verify QuantForge API integration. Run with backend on :8000."""

import os
import sys

try:
    import httpx
except ImportError:
    print("pip install httpx")
    sys.exit(1)

BASE = os.getenv("API_URL", "http://localhost:8000")
API = f"{BASE}/api/v1"
EMAIL = os.getenv("TEST_EMAIL", "verify@test.quantforge.io")
PASSWORD = "TestPass123!"


def main():
    client = httpx.Client(base_url=API, timeout=30.0)
    errors = []

    # Health
    r = httpx.get(f"{BASE}/health")
    print(f"[{'OK' if r.status_code == 200 else 'FAIL'}] GET /health -> {r.status_code}")
    if r.status_code != 200:
        errors.append("health")

    # Signup (may already exist)
    r = client.post("/auth/signup", json={
        "full_name": "Verify User",
        "email": EMAIL,
        "password": PASSWORD,
        "confirm_password": PASSWORD,
    })
    print(f"[{'OK' if r.status_code in (200, 201, 400) else 'FAIL'}] POST /auth/signup -> {r.status_code}")

    # Login
    r = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    ok = r.status_code == 200
    print(f"[{'OK' if ok else 'FAIL'}] POST /auth/login -> {r.status_code}")
    if not ok:
        errors.append("login")
        return print(f"\nFailed — is backend running at {BASE}?")

    cookies = r.cookies
    client.cookies.update(cookies)

    endpoints = [
        ("GET", "/auth/me"),
        ("GET", "/dashboard/overview"),
        ("GET", "/portfolios"),
        ("GET", "/strategies"),
        ("GET", "/notifications"),
        ("GET", "/ai/market-summary"),
        ("GET", "/logs/system"),
        ("GET", "/sessions"),
    ]

    for method, path in endpoints:
        r = client.request(method, path)
        status = "OK" if r.status_code == 200 else "FAIL"
        print(f"[{status}] {method} {path} -> {r.status_code}")
        if r.status_code != 200:
            errors.append(path)

    print(f"\n{'All checks passed' if not errors else f'Failures: {errors}'}")


if __name__ == "__main__":
    main()
