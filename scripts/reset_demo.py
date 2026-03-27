#!/usr/bin/env python3
"""Reset Aerospike demo state between dry-run arcs (DEMO-04 support).

Usage:
    python scripts/reset_demo.py [--host localhost] [--port 3000]

Truncates sentinel.episodes, sentinel.rules, sentinel.trust sets so the
next demo arc starts clean (rules generated in Attack 1 don't pre-exist).
"""
import argparse
import sys

import aerospike


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset Sentinel demo state")
    parser.add_argument("--host", default="localhost", help="Aerospike host")
    parser.add_argument("--port", type=int, default=3000, help="Aerospike port")
    args = parser.parse_args()

    namespace = "sentinel"
    sets_to_truncate = ["episodes", "rules", "trust"]

    try:
        config = {"hosts": [(args.host, args.port)]}
        client = aerospike.client(config).connect()
    except Exception as e:
        print(f"FAIL: Cannot connect to Aerospike at {args.host}:{args.port} -- {e}")
        return 1

    for set_name in sets_to_truncate:
        try:
            client.truncate(namespace, set_name, 0)
            print(f"  Truncated {namespace}.{set_name}")
        except aerospike.exception.InvalidRequest:
            print(f"  {namespace}.{set_name} -- does not exist yet (OK)")
        except Exception as e:
            print(f"  WARN: {namespace}.{set_name} -- {e}")

    client.close()
    print("\nDemo state reset complete -- ready for fresh arc.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
