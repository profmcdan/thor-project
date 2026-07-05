from django.urls import path
from transaction.views import DepositView, WithdrawalView, TransferView, WalletHistoryView
from transaction.admin_views import AdminDashboardStatsView, AdminTransactionListView, AdminWalletListView

urlpatterns = [
    path('wallets/<uuid:wallet_id>/history/', WalletHistoryView.as_view(), name='wallet_history'),
    path('transactions/deposit/', DepositView.as_view(), name='transaction_deposit'),
    path('transactions/withdraw/', WithdrawalView.as_view(), name='transaction_withdraw'),
    path('transactions/transfer/', TransferView.as_view(), name='transaction_transfer'),
    path('admin/dashboard/', AdminDashboardStatsView.as_view(), name='admin_dashboard'),
    path('admin/transactions/', AdminTransactionListView.as_view(), name='admin_transactions'),
    path('admin/wallets/', AdminWalletListView.as_view(), name='admin_wallets'),
]
