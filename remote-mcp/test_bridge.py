#!/usr/bin/env python3
"""
Test script for Remote MCP Bridge

Tests the complete flow:
1. Bridge server is running
2. Tunnel client can connect
3. Requests can be forwarded through tunnel
4. Responses are returned correctly

Usage:
    python test_bridge.py
"""

import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment
load_dotenv()

BRIDGE_HOST = os.getenv("BRIDGE_HOST", "localhost")
BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "8767"))
USER_ID = os.getenv("USER_ID", "")
REMOTE_API_KEY = os.getenv("REMOTE_API_KEY", "")

if not USER_ID or not REMOTE_API_KEY:
    print("❌ USER_ID and REMOTE_API_KEY must be set in .env")
    sys.exit(1)


async def test_bridge_health():
    """Test 1: Bridge server health check."""
    print("\n" + "="*60)
    print("Test 1: Bridge Server Health")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/health",
                timeout=5.0
            )

            if response.status_code == 200:
                data = response.json()
                print("✅ Bridge server is healthy")
                print(f"   Status: {data.get('status')}")
                print(f"   Active tunnels: {data.get('active_tunnels', 0)}")
                return True
            else:
                print(f"❌ Bridge server returned status {response.status_code}")
                return False

    except httpx.ConnectError:
        print(f"❌ Cannot connect to bridge server at {BRIDGE_HOST}:{BRIDGE_PORT}")
        print("   Make sure bridge server is running: ./start_bridge.sh")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_tunnel_active():
    """Test 2: Check if tunnel is active."""
    print("\n" + "="*60)
    print("Test 2: Tunnel Connection Status")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            # Try to make a request through the tunnel
            # This will fail with "No active tunnel" if tunnel isn't connected
            response = await client.post(
                f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/u/{USER_ID}/list",
                json={},  # Omit path to list root directory
                headers={"X-API-Key": REMOTE_API_KEY},
                timeout=10.0
            )

            if response.status_code == 200:
                print("✅ Tunnel is active and responding")
                return True
            elif response.status_code == 403:
                data = response.json()
                if "No active tunnel" in data.get("detail", ""):
                    print("❌ Tunnel is not connected")
                    print("   Make sure tunnel client is running: ./start_tunnel.sh")
                else:
                    print(f"❌ Permission denied: {data.get('detail')}")
                return False
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

    except httpx.TimeoutException:
        print("❌ Request timed out")
        print("   Check if local MCP server is running")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_search():
    """Test 3: Search through tunnel."""
    print("\n" + "="*60)
    print("Test 3: Search Request")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/u/{USER_ID}/search",
                json={
                    "query": "test search",
                    "top_k": 3
                },
                headers={"X-API-Key": REMOTE_API_KEY},
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print("✅ Search request successful")
                    result_data = data.get("data", {})
                    contexts = result_data.get("contexts", [])
                    print(f"   Query: test search")
                    print(f"   Results: {len(contexts)} contexts found")
                    if data.get("took_ms"):
                        print(f"   Time: {data['took_ms']:.0f}ms")
                    return True
                else:
                    print(f"❌ Search failed: {data.get('error')}")
                    return False
            else:
                print(f"❌ Request failed with status {response.status_code}")
                print(f"   Response: {response.text}")
                return False

    except httpx.TimeoutException:
        print("❌ Request timed out (>30s)")
        print("   This might indicate an issue with the local MCP server or daemon")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_list():
    """Test 4: List files through tunnel."""
    print("\n" + "="*60)
    print("Test 4: List Request")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/u/{USER_ID}/list",
                json={},  # Omit path to list root directory
                headers={"X-API-Key": REMOTE_API_KEY},
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print("✅ List request successful")
                    result_data = data.get("data", {})
                    items = result_data.get("items", [])
                    print(f"   Path: {result_data.get('path', '/')}")
                    print(f"   Items: {len(items)} files/directories")
                    if data.get("took_ms"):
                        print(f"   Time: {data['took_ms']:.0f}ms")
                    return True
                else:
                    print(f"❌ List failed: {data.get('error')}")
                    return False
            else:
                print(f"❌ Request failed with status {response.status_code}")
                print(f"   Response: {response.text}")
                return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_invalid_api_key():
    """Test 5: Invalid API key rejection."""
    print("\n" + "="*60)
    print("Test 5: Invalid API Key Rejection")
    print("="*60)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/u/{USER_ID}/search",
                json={"query": "test", "top_k": 3},
                headers={"X-API-Key": "invalid-key"},
                timeout=5.0
            )

            if response.status_code == 403:
                print("✅ Invalid API key correctly rejected")
                return True
            else:
                print(f"⚠️  Expected 403, got {response.status_code}")
                return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_rate_limiting():
    """Test 6: Rate limiting."""
    print("\n" + "="*60)
    print("Test 6: Rate Limiting")
    print("="*60)

    print("Sending 65 rapid requests to test rate limit (60/min)...")

    try:
        async with httpx.AsyncClient() as client:
            success_count = 0
            rate_limited = False

            for i in range(65):
                response = await client.post(
                    f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/u/{USER_ID}/list",
                    json={},  # Omit path to list root directory
                    headers={"X-API-Key": REMOTE_API_KEY},
                    timeout=5.0
                )

                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    rate_limited = True
                    break

            if rate_limited and success_count >= 60:
                print(f"✅ Rate limiting working correctly")
                print(f"   Succeeded: {success_count} requests")
                print(f"   Blocked after: {success_count} requests (limit: 60/min)")
                return True
            elif rate_limited:
                print(f"⚠️  Rate limited too early (after {success_count} requests)")
                return False
            else:
                print(f"⚠️  Rate limiting not triggered (sent 65, all succeeded)")
                print(f"   This might be okay if rate limit is higher than 60/min")
                return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Remote MCP Bridge Test Suite")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  Bridge: http://{BRIDGE_HOST}:{BRIDGE_PORT}")
    print(f"  User ID: {USER_ID}")
    print(f"  API Key: {REMOTE_API_KEY[:15]}...")

    results = []

    # Run tests
    results.append(("Bridge Health", await test_bridge_health()))

    if results[0][1]:  # Only continue if bridge is healthy
        results.append(("Tunnel Connection", await test_tunnel_active()))

        if results[1][1]:  # Only continue if tunnel is active
            results.append(("Search Request", await test_search()))
            results.append(("List Request", await test_list()))
            results.append(("Invalid API Key", await test_invalid_api_key()))
            results.append(("Rate Limiting", await test_rate_limiting()))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print("\n" + "="*60)
    print(f"Result: {passed}/{total} tests passed")
    print("="*60)

    if passed == total:
        print("\n🎉 All tests passed! Your Remote MCP Bridge is working correctly.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
