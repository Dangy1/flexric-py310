#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time

import requests


def main() -> int:
    parser = argparse.ArgumentParser(description="Read shared KPM indications from the FlexRIC KPM bus")
    parser.add_argument("--mode", choices=["rru", "ue", "all"], default="rru")
    parser.add_argument("--duration-s", type=int, default=30)
    parser.add_argument("--poll-ms", type=int, default=1000)
    parser.add_argument("--bus-url", default=None)
    args = parser.parse_args()

    base_url = (args.bus_url or '').strip() or sys.argv[0] and ''
    if not base_url:
        base_url = None
    base_url = base_url or __import__('os').getenv('KPM_BUS_URL', 'http://127.0.0.1:8091')
    base_url = base_url.rstrip('/')

    last_seq = 0
    started = time.time()
    printed_any = False
    print(f"Reading KPM bus mode='{args.mode}' from {base_url} for {args.duration_s}s")
    while True:
        if args.duration_s > 0 and (time.time() - started) >= args.duration_s:
            break
        response = requests.get(
            f"{base_url}/kpm/latest",
            params={"mode": args.mode, "after_seq": last_seq, "limit": 100},
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        records = payload.get("records", [])
        for event in records:
            print(event.get("raw", ""))
            last_seq = max(last_seq, int(event.get("seq", 0)))
            printed_any = True
        if not records:
            print("Still waiting for shared KPM bus indications...")
        time.sleep(max(args.poll_ms, 100) / 1000.0)

    if not printed_any:
        print("No KPM bus records were received in this window.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
