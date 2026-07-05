from rest_framework import generics, permissions
from wallet.models import Wallet
from wallet.serializers import WalletSerializer

class WalletListCreateView(generics.ListCreateAPIView):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return wallets belonging to the authenticated user
        return Wallet.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class WalletDetailView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only view their own wallets
        return Wallet.objects.filter(user=self.request.user)
