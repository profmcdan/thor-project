import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings

class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallets'
    )
    name = models.CharField(max_length=100, default="Default Wallet")
    currency = models.CharField(max_length=3, default="NGN")
    balance = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'currency', 'name'],
                name='unique_user_wallet_per_currency_name'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'currency']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.name} ({self.currency}): {self.balance}"
