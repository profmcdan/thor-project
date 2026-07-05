from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.core.cache import cache
from transaction.models import Transaction, LedgerEntry
from transaction.serializers import (
    TransactionSerializer, LedgerEntrySerializer,
    DepositSerializer, WithdrawalSerializer, TransferSerializer
)
from wallet.models import Wallet
from wallet.services import WalletService, WalletServiceException

class WalletHistoryView(generics.ListAPIView):
    """
    Returns chronological ledger entry list for a specific wallet owned by the user.
    """
    serializer_class = LedgerEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        wallet_id = self.kwargs.get('wallet_id')
        # Only allow users to view ledger entries for their own wallets
        return LedgerEntry.objects.filter(
            wallet_id=wallet_id,
            wallet__user=self.request.user
        ).order_by('-created_at')


class BaseTransactionView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_idempotency_key(self, request):
        key = request.headers.get('X-Idempotency-Key') or request.META.get('HTTP_X_IDEMPOTENCY_KEY')
        if not key or not key.strip():
            return None
        return key.strip()

    def handle_idempotent_request(self, request, serializer_class, action_func):
        key = self.get_idempotency_key(request)
        if not key:
            return Response(
                {"error": "X-Idempotency-Key HTTP header is required for transaction endpoints."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Check if transaction reference already exists in database
        existing_txn = Transaction.objects.filter(reference=key).first()
        if existing_txn:
            serializer = TransactionSerializer(existing_txn)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
                headers={"X-Cache-Lookup": "HIT"}
            )

        # 2. Acquire Redis distributed lock for this key to prevent race conditions
        lock_key = f"lock:idempotency:{key}"
        if not cache.add(lock_key, "processing", timeout=30):
            return Response(
                {"error": "A duplicate request is currently being processed. Please retry in a few seconds."},
                status=status.HTTP_409_CONFLICT
            )

        try:
            # 3. Validate and execute
            serializer = serializer_class(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            
            # Run transaction action via WalletService
            txn = action_func(serializer.validated_data, key)
            
            response_serializer = TransactionSerializer(txn)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        except WalletServiceException as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            # 4. Release lock
            cache.delete(lock_key)


class DepositView(BaseTransactionView):
    """
    API endpoint to deposit/fund a wallet.
    """
    serializer_class = DepositSerializer

    def post(self, request, *args, **kwargs):
        def action(validated_data, reference):
            return WalletService.deposit(
                wallet_id=validated_data['wallet_id'],
                amount=validated_data['amount'],
                reference=reference,
                description=validated_data.get('description')
            )
        return self.handle_idempotent_request(request, self.serializer_class, action)


class WithdrawalView(BaseTransactionView):
    """
    API endpoint to withdraw funds from a wallet.
    """
    serializer_class = WithdrawalSerializer

    def post(self, request, *args, **kwargs):
        def action(validated_data, reference):
            return WalletService.withdraw(
                wallet_id=validated_data['wallet_id'],
                amount=validated_data['amount'],
                reference=reference,
                description=validated_data.get('description')
            )
        return self.handle_idempotent_request(request, self.serializer_class, action)


class TransferView(BaseTransactionView):
    """
    API endpoint to transfer funds between wallets.
    """
    serializer_class = TransferSerializer

    def post(self, request, *args, **kwargs):
        def action(validated_data, reference):
            return WalletService.transfer(
                source_wallet_id=validated_data['source_wallet_id'],
                destination_wallet_id=validated_data['destination_wallet_id'],
                amount=validated_data['amount'],
                reference=reference,
                description=validated_data.get('description')
            )
        return self.handle_idempotent_request(request, self.serializer_class, action)
