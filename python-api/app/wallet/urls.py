from django.urls import path
from wallet.views import WalletListCreateView, WalletDetailView

urlpatterns = [
    path('wallets/', WalletListCreateView.as_view(), name='wallet_list_create'),
    path('wallets/<uuid:pk>/', WalletDetailView.as_view(), name='wallet_detail'),
]
