import uuid
from decimal import Decimal
from django.db import transaction, IntegrityError
from wallet.models import Wallet
from transaction.models import Transaction, LedgerEntry

class WalletServiceException(Exception):
    """Base exception for Wallet Service errors."""
    pass

class InsufficientFundsError(WalletServiceException):
    """Raised when a wallet has insufficient funds for a debit operation."""
    pass

class WalletNotFoundError(WalletServiceException):
    """Raised when a wallet cannot be found."""
    pass

class TransactionError(WalletServiceException):
    """Raised when a transaction check fails."""
    pass

class WalletService:
    @staticmethod
    def deposit(wallet_id: uuid.UUID, amount: Decimal, reference: str, description: str = None) -> Transaction:
        """
        Credit a wallet.
        """
        if amount <= 0:
            raise ValueError("Deposit amount must be greater than zero.")

        with transaction.atomic():
            try:
                wallet = Wallet.objects.select_for_update().get(id=wallet_id)
            except Wallet.DoesNotExist:
                raise WalletNotFoundError(f"Wallet with ID {wallet_id} does not exist.")

            # Create Transaction Record. If reference exists, database unique constraint raises IntegrityError
            try:
                txn = Transaction.objects.create(
                    reference=reference,
                    transaction_type=Transaction.TransactionType.DEPOSIT,
                    amount=amount,
                    currency=wallet.currency,
                    status=Transaction.Status.SUCCESS,
                    description=description or "Wallet deposit"
                )
            except IntegrityError:
                raise TransactionError(f"Transaction with reference {reference} already exists.")

            # Update Wallet Balance
            wallet.balance += amount
            wallet.save()

            # Create Ledger Entry
            LedgerEntry.objects.create(
                transaction=txn,
                wallet=wallet,
                amount=amount,
                entry_type=LedgerEntry.EntryType.CREDIT,
                balance_after=wallet.balance
            )

            return txn

    @staticmethod
    def withdraw(wallet_id: uuid.UUID, amount: Decimal, reference: str, description: str = None) -> Transaction:
        """
        Debit a wallet (simulate outward transfer or withdrawal).
        """
        if amount <= 0:
            raise ValueError("Withdrawal amount must be greater than zero.")

        with transaction.atomic():
            try:
                wallet = Wallet.objects.select_for_update().get(id=wallet_id)
            except Wallet.DoesNotExist:
                raise WalletNotFoundError(f"Wallet with ID {wallet_id} does not exist.")

            if wallet.balance < amount:
                raise InsufficientFundsError(f"Insufficient funds in wallet {wallet_id}.")

            # Create Transaction Record. If reference exists, unique constraint raises IntegrityError
            try:
                txn = Transaction.objects.create(
                    reference=reference,
                    transaction_type=Transaction.TransactionType.WITHDRAWAL,
                    amount=amount,
                    currency=wallet.currency,
                    status=Transaction.Status.SUCCESS,
                    description=description or "Wallet withdrawal"
                )
            except IntegrityError:
                raise TransactionError(f"Transaction with reference {reference} already exists.")

            # Update Wallet Balance
            wallet.balance -= amount
            wallet.save()

            # Create Ledger Entry
            LedgerEntry.objects.create(
                transaction=txn,
                wallet=wallet,
                amount=-amount,
                entry_type=LedgerEntry.EntryType.DEBIT,
                balance_after=wallet.balance
            )

            return txn

    @staticmethod
    def transfer(source_wallet_id: uuid.UUID, destination_wallet_id: uuid.UUID, amount: Decimal, reference: str, description: str = None) -> Transaction:
        """
        Transfer funds from one wallet to another.
        Uses ordered locking by wallet UUID to avoid deadlocks.
        """
        if source_wallet_id == destination_wallet_id:
            raise ValueError("Cannot transfer to the same wallet.")

        if amount <= 0:
            raise ValueError("Transfer amount must be greater than zero.")

        # Sort the IDs to ensure deterministic locking order
        sorted_ids = sorted([source_wallet_id, destination_wallet_id])

        with transaction.atomic():
            # Acquire locks in sorted order
            locked_wallets_qs = Wallet.objects.select_for_update().filter(id__in=sorted_ids).order_by('id')
            locked_wallets_dict = {w.id: w for w in locked_wallets_qs}

            if len(locked_wallets_dict) != 2:
                raise WalletNotFoundError("One or both wallets could not be found.")

            source_wallet = locked_wallets_dict[source_wallet_id]
            destination_wallet = locked_wallets_dict[destination_wallet_id]

            if source_wallet.currency != destination_wallet.currency:
                raise ValueError("Currency mismatch. Multi-currency transfers are not supported directly.")

            if source_wallet.balance < amount:
                raise InsufficientFundsError(f"Insufficient funds in source wallet {source_wallet_id}.")

            # Create Transaction Header. Catch database-level unique reference constraint violations
            try:
                txn = Transaction.objects.create(
                    reference=reference,
                    transaction_type=Transaction.TransactionType.TRANSFER,
                    amount=amount,
                    currency=source_wallet.currency,
                    status=Transaction.Status.SUCCESS,
                    description=description or "Wallet-to-wallet transfer"
                )
            except IntegrityError:
                raise TransactionError(f"Transaction with reference {reference} already exists.")

            # Update Balances
            source_wallet.balance -= amount
            source_wallet.save()

            destination_wallet.balance += amount
            destination_wallet.save()

            # Bulk create Ledger Entries in a single SQL operation (saves 1 round trip)
            LedgerEntry.objects.bulk_create([
                LedgerEntry(
                    transaction=txn,
                    wallet=source_wallet,
                    amount=-amount,
                    entry_type=LedgerEntry.EntryType.DEBIT,
                    balance_after=source_wallet.balance
                ),
                LedgerEntry(
                    transaction=txn,
                    wallet=destination_wallet,
                    amount=amount,
                    entry_type=LedgerEntry.EntryType.CREDIT,
                    balance_after=destination_wallet.balance
                )
            ])

            return txn
