# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests",
# ]
# ///

import os
import sys
import uuid
import time
import random
import concurrent.futures
from decimal import Decimal
import requests

# Target API URL (running via docker-compose on port 8005)
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8005")
API_URL = f"{BASE_URL}/api"

NUM_USERS = 50
NUM_THREADS = 10
TOTAL_TRANSFERS = 5000

print(f"=== Wallet System High Concurrent Traffic Simulator ===")
print(f"Target API Endpoint: {API_URL}")
print(f"Configuration: {NUM_USERS} Users | {NUM_THREADS} Worker Threads | {TOTAL_TRANSFERS} Transfers\n")

# Session with optimized connection pooling for high concurrency
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=NUM_THREADS, pool_maxsize=NUM_THREADS)
session.mount('http://', adapter)
session.mount('https://', adapter)

users = []
wallets = {}  # user_id -> wallet_id
tokens = {}   # user_id -> access_token

# Stats counters
stats = {
    "success": 0,
    "idempotent_hits": 0,
    "insufficient_funds": 0,
    "concurrency_conflicts": 0,
    "errors": 0,
    "total_requests": 0
}

def register_user(i):
    email = f"loadtest_{uuid.uuid4().hex[:8]}@example.com"
    password = "LoadTestPassword123!"
    
    # 1. Register User
    try:
        reg_resp = session.post(f"{API_URL}/auth/register/", json={
            "email": email,
            "password": password,
            "first_name": f"User_{i}",
            "last_name": "Simulator"
        }, timeout=30)
        
        if reg_resp.status_code != 201:
            print(f"Failed to register user {i}: {reg_resp.text}")
            return None
            
        data = reg_resp.json()
        user_id = data["user"]["id"]
        token = data["tokens"]["access"]
        
        # 2. Create NGN Wallet
        headers = {"Authorization": f"Bearer {token}"}
        wallet_resp = session.post(f"{API_URL}/wallets/", json={
            "name": "Primary Wallet",
            "currency": "NGN"
        }, headers=headers, timeout=30)
        
        if wallet_resp.status_code != 201:
            print(f"Failed to create wallet for user {i}: {wallet_resp.text}")
            return None
            
        wallet_id = wallet_resp.json()["id"]
        
        # 3. Fund Wallet (Deposit 10,000 NGN)
        dep_resp = session.post(
            f"{API_URL}/transactions/deposit/", 
            json={
                "wallet_id": wallet_id,
                "amount": "10000.0000",
                "description": "Initial funding"
            },
            headers={
                **headers,
                "X-Idempotency-Key": str(uuid.uuid4())
            },
            timeout=30
        )
        
        if dep_resp.status_code != 201:
            print(f"Failed to fund wallet for user {i}: {dep_resp.text}")
            return None
            
        print(f"Created & Funded User {i}: {email} | Wallet: {wallet_id}")
        return {
            "id": user_id,
            "email": email,
            "token": token,
            "wallet_id": wallet_id
        }
    except Exception as e:
        print(f"Network error creating user {i}: {e}")
        return None

# Wait for the backend server to boot and migrations to complete
print("Checking if backend API is online and ready...")
while True:
    try:
        # A dummy POST to register will return 400 (Bad Request) if Django is ready,
        # or 502 (Bad Gateway) if Nginx is up but Gunicorn is still booting.
        resp = session.post(f"{API_URL}/auth/register/", json={}, timeout=2)
        if resp.status_code != 502:
            print("Backend API is online and ready!\n")
            break
        print("Backend is booting up (received 502 from Nginx). Retrying in 2s...")
    except Exception:
        print("Backend is unreachable. Retrying in 2s...")
    time.sleep(2)

# Step 1: Initialize users and wallets
print("Step 1: Provisioning users and wallets...")
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(register_user, i) for i in range(NUM_USERS)]
    for f in concurrent.futures.as_completed(futures):
        res = f.result()
        if res:
            users.append(res)
            wallets[res["id"]] = res["wallet_id"]
            tokens[res["id"]] = res["token"]

if len(users) < 2:
    print("Error: Need at least 2 successful users to run simulation. Check if the server is running.")
    sys.exit(1)

print(f"\nSuccessfully provisioned {len(users)} users. Initial system total: {len(users) * 10000} NGN.")

# Step 2: Fire concurrent transfers
print("\nStep 2: Simulating highly concurrent transactions...")
start_time = time.time()

def perform_random_transfer(index):
    # Choose random sender & receiver
    sender = random.choice(users)
    receiver = random.choice(users)
    while receiver["id"] == sender["id"]:
        receiver = random.choice(users)
        
    amount = round(random.uniform(50.0, 200.0), 2)
    ref_key = str(uuid.uuid4())
    
    payload = {
        "source_wallet_id": sender["wallet_id"],
        "destination_wallet_id": receiver["wallet_id"],
        "amount": f"{amount:.4f}",
        "description": f"Simulation txn {index}"
    }
    
    headers = {
        "Authorization": f"Bearer {sender['token']}",
        "X-Idempotency-Key": ref_key
    }
    
    # Randomly decide to fire a duplicate request immediately to test idempotency locks
    fire_duplicate = random.random() < 0.15
    
    def send_req(req_headers):
        stats["total_requests"] += 1
        try:
            resp = session.post(
                f"{API_URL}/transactions/transfer/",
                json=payload,
                headers=req_headers,
                timeout=30
            )
            
            if resp.status_code == 201:
                stats["success"] += 1
            elif resp.status_code == 200 and resp.headers.get("X-Cache-Lookup") == "HIT":
                stats["idempotent_hits"] += 1
            elif resp.status_code == 400:
                stats["insufficient_funds"] += 1
            elif resp.status_code == 409:
                stats["concurrency_conflicts"] += 1
            else:
                stats["errors"] += 1
                # print(f"Unexpected response [{resp.status_code}]: {resp.text}")
        except Exception as e:
            stats["errors"] += 1
            # print(f"Request failed: {e}")

    # Fire primary request
    send_req(headers)
    
    # If chosen, fire duplicate key concurrently
    if fire_duplicate:
        # Mini sleep delay to simulate micro-seconds race condition
        time.sleep(0.002)
        send_req(headers)

# Use ThreadPoolExecutor to simulate concurrent clients
with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
    executor.map(perform_random_transfer, range(TOTAL_TRANSFERS))

end_time = time.time()
elapsed = end_time - start_time

print("\nStep 3: Compiling results...")
print(f"Elapsed Time: {elapsed:.2f} seconds")
print(f"Throughput: {stats['total_requests'] / elapsed:.2f} requests/sec")
print("\nSimulation Statistics:")
print(f"  - Total API Requests:     {stats['total_requests']}")
print(f"  - Successful Transfers:   {stats['success']}")
print(f"  - Blocked Duplicates:     {stats['idempotent_hits']} (Idempotency Key HIT)")
print(f"  - Insufficient Funds:     {stats['insufficient_funds']}")
print(f"  - Concurrency Lock Fails: {stats['concurrency_conflicts']}")
print(f"  - Errors / Timeouts:      {stats['errors']}")

# Step 4: Reconcile and audit balances to check system integrity
print("\nStep 4: Performing ledger integrity check and balance reconciliation...")
total_final_balance = Decimal("0.0000")

for user in users:
    headers = {"Authorization": f"Bearer {user['token']}"}
    try:
        resp = session.get(f"{API_URL}/wallets/{user['wallet_id']}/", headers=headers, timeout=15)
        if resp.status_code == 200:
            bal = Decimal(resp.json()["balance"])
            total_final_balance += bal
            # print(f"  - {user['email']}: {bal} NGN")
        else:
            print(f"  - Failed to fetch balance for {user['email']}: {resp.text}")
    except Exception as e:
        print(f"  - Error querying balance for {user['email']}: {e}")

expected_total = Decimal(NUM_USERS * 10000)
discrepancy = total_final_balance - expected_total

print(f"\nReconciliation Summary:")
print(f"  - Expected System Total:  {expected_total:.4f} NGN")
print(f"  - Actual System Total:    {total_final_balance:.4f} NGN")
print(f"  - Discrepancy:            {discrepancy:.4f} NGN")

if discrepancy == Decimal("0.0000"):
    print("\n[SUCCESS] Balance reconciliation matched perfectly! The database row locking and ledger transactions successfully prevented double spending or balance loss.")
else:
    print("\n[FAILURE] Balance mismatch found! Double spending or transaction leak occurred.")

# Save report to JSON file if environment variable is set
report_file = os.environ.get("TRAFFIC_SIM_REPORT_FILE")
if report_file:
    import json
    report_data = {
        "elapsed_time": round(elapsed, 4),
        "throughput": round(stats['total_requests'] / elapsed, 2),
        "total_requests": stats['total_requests'],
        "success": stats['success'],
        "idempotent_hits": stats['idempotent_hits'],
        "insufficient_funds": stats['insufficient_funds'],
        "concurrency_conflicts": stats['concurrency_conflicts'],
        "errors": stats['errors'],
        "reconciliation_expected": str(expected_total),
        "reconciliation_actual": str(total_final_balance),
        "reconciliation_discrepancy": str(discrepancy)
    }
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=4)
    print(f"\nStats report successfully saved to {report_file}")

