from decimal import Decimal
import uuid
import concurrent.futures
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.core.cache import cache
from django.db import connection
from rest_framework.test import APIClient
from rest_framework import status
from wallet.models import Wallet
from wallet.services import WalletService, InsufficientFundsError
from transaction.models import Transaction, LedgerEntry

User = get_user_model()

class WalletTransactionTests(TransactionTestCase):
    def setUp(self):
        # Clear cache between tests to avoid idempotency pollution
        cache.clear()
        
        self.client = APIClient()
        self.user1 = User.objects.create_user(email="alice@example.com", password="password123")
        self.user2 = User.objects.create_user(email="bob@example.com", password="password123")
        
        # Get JWT tokens for authentication
        self.client.force_authenticate(user=self.user1)

        # Create initial wallets
        self.wallet_alice = Wallet.objects.create(
            user=self.user1,
            name="Alice Savings",
            currency="NGN",
            balance=Decimal("1000.0000")
        )
        self.wallet_bob = Wallet.objects.create(
            user=self.user2,
            name="Bob Savings",
            currency="NGN",
            balance=Decimal("0.0000")
        )

    def test_user_registration_and_login(self):
        self.client.force_authenticate(user=None) # Log out
        
        # Test Registration
        reg_payload = {
            "email": "charlie@example.com",
            "password": "securepassword",
            "first_name": "Charlie",
            "last_name": "Brown"
        }
        response = self.client.post("/api/auth/register/", reg_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        
        # Test Login
        login_payload = {
            "email": "charlie@example.com",
            "password": "securepassword"
        }
        response = self.client.post("/api/auth/login/", login_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_create_and_list_wallets(self):
        # List Wallets
        response = self.client.get("/api/wallets/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Alice Savings")

        # Create New Wallet
        payload = {
            "name": "Alice Business",
            "currency": "USD"
        }
        response = self.client.post("/api/wallets/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["currency"], "USD")
        self.assertEqual(float(response.data["balance"]), 0.0)

        # Ensure duplicate name & currency combination per user is rejected
        response = self.client.post("/api/wallets/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deposit_endpoint_with_idempotency(self):
        url = "/api/transactions/deposit/"
        payload = {
            "wallet_id": str(self.wallet_alice.id),
            "amount": "500.0000",
            "description": "Salary payment"
        }
        
        # Missing Idempotency Key header should be rejected
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Success path with Idempotency Key
        idempotency_key = str(uuid.uuid4())
        response = self.client.post(
            url, 
            payload, 
            format="json", 
            HTTP_X_IDEMPOTENCY_KEY=idempotency_key
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "SUCCESS")
        
        # Verify wallet balance was updated
        self.wallet_alice.refresh_from_db()
        self.assertEqual(self.wallet_alice.balance, Decimal("1500.0000"))

        # Re-sending the same request with the same key should return HIT
        response = self.client.post(
            url, 
            payload, 
            format="json", 
            HTTP_X_IDEMPOTENCY_KEY=idempotency_key
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get("X-Cache-Lookup"), "HIT")

        # Verify wallet balance was NOT updated again (remains 1500)
        self.wallet_alice.refresh_from_db()
        self.assertEqual(self.wallet_alice.balance, Decimal("1500.0000"))

    def test_withdrawal_endpoint(self):
        url = "/api/transactions/withdraw/"
        payload = {
            "wallet_id": str(self.wallet_alice.id),
            "amount": "300.0000",
            "description": "ATM cash withdrawal"
        }
        idempotency_key = str(uuid.uuid4())
        
        response = self.client.post(
            url, 
            payload, 
            format="json", 
            HTTP_X_IDEMPOTENCY_KEY=idempotency_key
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.wallet_alice.refresh_from_db()
        self.assertEqual(self.wallet_alice.balance, Decimal("700.0000"))
        
        # Test insufficient funds withdrawal
        payload_large = {
            "wallet_id": str(self.wallet_alice.id),
            "amount": "1000.0000"
        }
        response = self.client.post(
            url, 
            payload_large, 
            format="json", 
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_endpoint(self):
        url = "/api/transactions/transfer/"
        payload = {
            "source_wallet_id": str(self.wallet_alice.id),
            "destination_wallet_id": str(self.wallet_bob.id),
            "amount": "250.0000",
            "description": "Dinner split"
        }
        idempotency_key = str(uuid.uuid4())

        response = self.client.post(
            url, 
            payload, 
            format="json", 
            HTTP_X_IDEMPOTENCY_KEY=idempotency_key
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.wallet_alice.refresh_from_db()
        self.wallet_bob.refresh_from_db()
        
        self.assertEqual(self.wallet_alice.balance, Decimal("750.0000"))
        self.assertEqual(self.wallet_bob.balance, Decimal("250.0000"))

        # Verify ledger entries are correctly created (1 Debit, 1 Credit)
        txn = Transaction.objects.get(reference=idempotency_key)
        ledger_entries = LedgerEntry.objects.filter(transaction=txn)
        self.assertEqual(ledger_entries.count(), 2)
        
        debit_entry = ledger_entries.get(entry_type=LedgerEntry.EntryType.DEBIT)
        credit_entry = ledger_entries.get(entry_type=LedgerEntry.EntryType.CREDIT)
        
        self.assertEqual(debit_entry.wallet, self.wallet_alice)
        self.assertEqual(debit_entry.amount, Decimal("-250.0000"))
        self.assertEqual(debit_entry.balance_after, Decimal("750.0000"))
        
        self.assertEqual(credit_entry.wallet, self.wallet_bob)
        self.assertEqual(credit_entry.amount, Decimal("250.0000"))
        self.assertEqual(credit_entry.balance_after, Decimal("250.0000"))

    def test_concurrency_locking(self):
        """
        Runs multiple concurrent transfers from Alice to Bob in separate threads
        to ensure race conditions/double spending are prevented by select_for_update.
        """
        # Alice starts with 1000 NGN.
        # Bob starts with 0 NGN.
        # We spin up 10 concurrent threads, each trying to transfer 100 NGN.
        # Total transfer = 10 * 100 = 1000 NGN.
        # Final Alice balance must be 0 NGN. Bob balance must be 1000 NGN.
        
        def run_transfer(index):
            ref = f"concurrent-transfer-{index}"
            try:
                WalletService.transfer(
                    source_wallet_id=self.wallet_alice.id,
                    destination_wallet_id=self.wallet_bob.id,
                    amount=Decimal("100.0000"),
                    reference=ref,
                    description="Concurrent test"
                )
                return True
            except Exception as e:
                return e
            finally:
                from django.db import connections
                connections.close_all()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Start the transfer threads
            futures = [executor.submit(run_transfer, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Refresh from database
        self.wallet_alice.refresh_from_db()
        self.wallet_bob.refresh_from_db()

        if connection.vendor == 'sqlite':
            # SQLite does database-level locking, which causes concurrent threads to fail
            # with "database is locked". We verify that for the threads that DID succeed,
            # the balances and ledgers are fully consistent.
            successful_transfers = results.count(True)
            self.assertGreater(successful_transfers, 0)
            
            expected_alice = Decimal("1000.0000") - (successful_transfers * Decimal("100.0000"))
            expected_bob = Decimal("0.0000") + (successful_transfers * Decimal("100.0000"))
            self.assertEqual(self.wallet_alice.balance, expected_alice)
            self.assertEqual(self.wallet_bob.balance, expected_bob)

            total_debits = LedgerEntry.objects.filter(wallet=self.wallet_alice, entry_type=LedgerEntry.EntryType.DEBIT).count()
            total_credits = LedgerEntry.objects.filter(wallet=self.wallet_bob, entry_type=LedgerEntry.EntryType.CREDIT).count()
            self.assertEqual(total_debits, successful_transfers)
            self.assertEqual(total_credits, successful_transfers)
        else:
            # PostgreSQL supports row-level select_for_update locking, so all 10 threads succeed.
            self.assertEqual(results.count(True), 10)
            self.assertEqual(self.wallet_alice.balance, Decimal("0.0000"))
            self.assertEqual(self.wallet_bob.balance, Decimal("1000.0000"))

            total_debits = LedgerEntry.objects.filter(wallet=self.wallet_alice, entry_type=LedgerEntry.EntryType.DEBIT).count()
            total_credits = LedgerEntry.objects.filter(wallet=self.wallet_bob, entry_type=LedgerEntry.EntryType.CREDIT).count()
            self.assertEqual(total_debits, 10)
            self.assertEqual(total_credits, 10)
