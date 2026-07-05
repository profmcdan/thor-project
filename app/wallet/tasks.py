import logging
from decimal import Decimal
from celery import shared_task
from django.db.models import Sum
from wallet.models import Wallet
from transaction.models import LedgerEntry

logger = logging.getLogger(__name__)

@shared_task
def audit_wallet_balances():
    """
    Periodic task to reconcile wallet cached balances against ledger history.
    """
    logger.info("Starting wallet ledger audit...")
    mismatches = []
    
    # Query all wallets
    wallets = Wallet.objects.all()
    
    for wallet in wallets:
        # Sum of all ledger entries for this wallet
        ledger_sum = LedgerEntry.objects.filter(wallet=wallet).aggregate(total=Sum('amount'))['total'] or Decimal('0.0000')
        
        # Compare with wallet balance (using rounding/epsilon or exact check since both are Decimal)
        if abs(wallet.balance - ledger_sum) > Decimal('0.0000'):
            mismatches.append({
                "wallet_id": str(wallet.id),
                "user": wallet.user.email,
                "wallet_balance": str(wallet.balance),
                "ledger_sum": str(ledger_sum),
                "discrepancy": str(wallet.balance - ledger_sum)
            })
            
    if mismatches:
        logger.error(
            f"AUDIT FAILED: Found {len(mismatches)} wallet balance discrepancies!"
        )
        for mismatch in mismatches:
            logger.error(
                f"Wallet {mismatch['wallet_id']} ({mismatch['user']}) balance is {mismatch['wallet_balance']} "
                f"but sum of ledger entries is {mismatch['ledger_sum']}. Discrepancy: {mismatch['discrepancy']}"
            )
    else:
        logger.info("AUDIT SUCCESS: All wallet balances match ledger history.")
        
    return {
        "status": "success" if not mismatches else "failed",
        "mismatch_count": len(mismatches),
        "mismatches": mismatches
    }
