from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Sum
from decimal import Decimal
from wallet.models import Wallet
from transaction.models import Transaction
from transaction.serializers import TransactionSerializer
from wallet.serializers import WalletSerializer
from core.pagination import StandardResultsSetPagination

User = get_user_model()

class AdminDashboardStatsView(generics.GenericAPIView):
    """
    Staff-only view returning system-wide fintech statistics.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        users_count = User.objects.count()
        wallets_count = Wallet.objects.count()
        
        # Calculate sum of all NGN and USD wallet balances
        total_ngn_balance = Wallet.objects.filter(currency="NGN").aggregate(total=Sum('balance'))['total'] or Decimal('0.0000')
        total_usd_balance = Wallet.objects.filter(currency="USD").aggregate(total=Sum('balance'))['total'] or Decimal('0.0000')
        
        total_transactions = Transaction.objects.count()

        return Response({
            "users_count": users_count,
            "wallets_count": wallets_count,
            "total_ngn_balance": str(total_ngn_balance),
            "total_usd_balance": str(total_usd_balance),
            "total_transactions": total_transactions,
        }, status=status.HTTP_200_OK)

class AdminTransactionListView(generics.ListAPIView):
    """
    Staff-only view returning a paginated, searchable history of all transactions.
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = TransactionSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference', 'description', 'transaction_type', 'status', 'currency']
    ordering_fields = ['created_at', 'amount']
    queryset = Transaction.objects.all().order_by('-created_at')

class AdminWalletListView(generics.ListAPIView):
    """
    Staff-only view returning a paginated, searchable list of all wallets.
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = WalletSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__email', 'name', 'currency']
    ordering_fields = ['created_at', 'balance']
    queryset = Wallet.objects.all().order_by('-created_at')
