#!/usr/bin/env python3
"""
Test telemetry sender - sends mock telemetry data to the API to test WebSocket delivery.

Usage:
    python test_telemetry.py --team-id <team-id> --agent-name <agent-name> [--count 10] [--interval 2]

This sends mock telemetry data through the EXACT same endpoint that the orchestrator uses,
allowing you to test the WebSocket connection without running a full team.
"""

import argparse
import time
import requests
from datetime import datetime

def send_test_telemetry(api_url: str, team_id: str, agent_name: str, counter: int):
    """
    Send one batch of test telemetry data to the API.

    Uses the exact same schema as the orchestrator's telemetry collector.
    """
    url = f"{api_url}/api/telemetry/agent/{agent_name}"

    # Create mock telemetry data matching the exact schema
    payload = {
        "team_id": team_id,
        "agent_name": agent_name,
        "process_metrics": {
            "pid": 12345,
            "cpu_percent": 15.5 + (counter % 10),
            "memory_mb": 256.0 + (counter * 2),
            "threads": 8,
            "status": "running"
        },
        "token_usage": {
            "model": "claude-sonnet-4-5",
            "input_tokens": 1000 * counter,
            "output_tokens": 500 * counter,
            "total_tokens": 1500 * counter,
            "cost_usd": 0.01 * counter
        },
        "git_activities": [
            {
                "operation": "commit",
                "branch": "feature/test",
                "message": f"Test commit #{counter}",
                "files_changed": 3,
                "timestamp": datetime.utcnow().isoformat(),
                "agent_name": agent_name
            }
        ],
        "activity_logs": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "info",
                "message": f"Test activity log entry #{counter}",
                "source": "test_script",
                "agent_name": agent_name
            }
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        response = requests.post(url, json=payload, timeout=5)

        if response.status_code == 200:
            print(f"✓ Sent telemetry #{counter} - {response.json()['message']}")
            return True
        else:
            print(f"✗ Failed: HTTP {response.status_code} - {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"✗ Failed: Could not connect to API at {api_url}")
        print("  Make sure the API server is running (./start.sh)")
        return False
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Send test telemetry data to verify WebSocket delivery"
    )
    parser.add_argument(
        "--team-id",
        required=True,
        help="Team ID (get from dashboard URL or database)"
    )
    parser.add_argument(
        "--agent-name",
        default="TestAgent",
        help="Agent name to use in telemetry (default: TestAgent)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of telemetry batches to send (default: 10)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Seconds between each batch (default: 2.0)"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API URL (default: http://localhost:8000)"
    )

    args = parser.parse_args()

    print("="*60)
    print("  Telemetry Test Script")
    print("="*60)
    print(f"  API URL: {args.api_url}")
    print(f"  Team ID: {args.team_id}")
    print(f"  Agent Name: {args.agent_name}")
    print(f"  Count: {args.count}")
    print(f"  Interval: {args.interval}s")
    print("="*60)
    print()
    print("Sending telemetry data...")
    print("(Watch the dashboard to see if it appears in the agent card)")
    print()

    success_count = 0

    for i in range(1, args.count + 1):
        if send_test_telemetry(args.api_url, args.team_id, args.agent_name, i):
            success_count += 1

        # Sleep before next batch (except after last one)
        if i < args.count:
            time.sleep(args.interval)

    print()
    print("="*60)
    print(f"  Complete: {success_count}/{args.count} batches sent successfully")
    print("="*60)

    if success_count == 0:
        exit(1)


if __name__ == "__main__":
    main()
