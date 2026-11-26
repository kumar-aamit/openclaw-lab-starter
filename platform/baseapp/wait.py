"""Wait until the app URL serves a given commit: python -m baseapp.wait"""
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable


def _fetch_json(url: str, insecure: bool) -> dict:
    context = ssl._create_unverified_context() if insecure else None
    with urllib.request.urlopen(url, timeout=5, context=context) as response:
        return json.load(response)


def wait_for_commit(
    url: str,
    commit: str,
    timeout: float = 300,
    interval: float = 2,
    insecure: bool = True,
    fetch: Callable[[str], dict] | None = None,
) -> float:
    fetch = fetch or (lambda u: _fetch_json(u, insecure))
    version_url = f"{url.rstrip('/')}/api/version"
    start = time.monotonic()
    seen = "nothing (unreachable)"
    while True:
        try:
            seen = fetch(version_url).get("commit") or "no commit"
        except (OSError, ValueError):
            pass
        elapsed = time.monotonic() - start
        if seen == commit:
            return elapsed
        if elapsed >= timeout:
            raise TimeoutError(f"{url} still reports {seen} after {timeout:g} s; expected {commit}")
        time.sleep(interval)


def main() -> int:
    url = os.environ.get("APP_URL", "").strip()
    if not url:
        print("APP_URL is not set; add it to lab.env", file=sys.stderr)
        return 2
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    insecure = os.environ.get("INSECURE_TLS", "1") == "1"
    print(f"waiting for {url} to serve {commit[:7]} ...", flush=True)
    try:
        elapsed = wait_for_commit(url, commit, insecure=insecure)
    except TimeoutError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"live in {elapsed:.0f} s at {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
