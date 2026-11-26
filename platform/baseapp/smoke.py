"""`make smoke`: run every example against the deployed app and print the timings."""
import os
import sys
import time

import httpx


def http_fetch(insecure: bool):
    client = httpx.Client(verify=not insecure, timeout=180.0)

    def fetch(method: str, url: str, body: dict | None = None):
        r = client.request(method, url, json=body)
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    return fetch


def main(url: str | None = None, fetch=None, insecure: bool | None = None) -> int:
    url = (url or os.environ.get("APP_URL", "")).rstrip("/")
    if not url:
        print("Set APP_URL in lab.env to your app's address.")
        return 1
    if insecure is None:
        insecure = os.environ.get("INSECURE_TLS", "1") == "1"
    fetch = fetch or http_fetch(insecure)

    status, screens = fetch("GET", f"{url}/api/screens")
    if status != 200:
        print(f"FAIL  {url}/api/screens answered HTTP {status}")
        return 1
    if not screens:
        print("The app has no screens yet.")
        return 1

    failures = 0
    for screen in screens:
        for i, label in enumerate(screen["examples"]):
            started = time.perf_counter()
            status, body = fetch("POST", f"{url}/api/screens/{screen['name']}/run", {"example": i})
            total = time.perf_counter() - started
            where = f"{screen['name']:<14} {label[:30]:<30}"
            if status != 200:
                failures += 1
                print(f"FAIL  {where} {body.get('error', status)}")
            elif body["mocked"]:
                print(f"ok    {where} {total:6.2f} s  mock answer (LLM_MOCK=1 on the server)")
            else:
                model_s = (body["timings"]["model_ms"] or 0) / 1000
                print(f"ok    {where} {total:6.2f} s  {body['tier']} model {model_s:.2f} s  {body['model']}")
    print("\nAll examples answered." if not failures else f"\n{failures} example(s) failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
