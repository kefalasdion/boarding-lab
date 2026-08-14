#!/usr/bin/env bash
set -euo pipefail

smoke_port="$(python3 - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    print(sock.getsockname()[1])
PY
)"

python3 -m boarding_sim --port "$smoke_port" > /tmp/boarding-lab-smoke.log 2>&1 &
smoke_pid=$!
cleanup() {
  kill "$smoke_pid" 2>/dev/null || true
  wait "$smoke_pid" 2>/dev/null || true
}
trap cleanup EXIT

SMOKE_PORT="$smoke_port" python3 - <<'PY'
import json
import os
import time
import urllib.request

base = f"http://127.0.0.1:{os.environ['SMOKE_PORT']}"
for _attempt in range(100):
    try:
        with urllib.request.urlopen(base + "/api/config", timeout=1) as response:
            config = json.load(response)
        break
    except Exception:
        time.sleep(0.1)
else:
    raise SystemExit("Server did not become ready")

assert config["modelVersion"]
with urllib.request.urlopen(base + "/", timeout=5) as response:
    assert b"Boarding Lab" in response.read()
with urllib.request.urlopen(base + "/data/default-comparison.json", timeout=15) as response:
    artifact = json.load(response)
assert artifact["summary"]["requested_runs"] == 100

request = urllib.request.Request(
    base + "/api/run",
    data=json.dumps({"scenario": {"aircraft": {"loadFactor": 0.05}}, "seed": 77}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=30) as response:
    result = json.load(response)
assert result["status"] == "valid"
assert result["metrics"]["seated_count"] == 9
print("Standalone smoke passed")
PY
