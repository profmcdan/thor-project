using System.ComponentModel.DataAnnotations.Schema;

namespace DotnetApi.Models;

[Table("transaction_ledgerentry")]
public class LedgerEntry
{
    [Column("id")]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Column("transaction_id")]
    public Guid TransactionId { get; set; }

    [ForeignKey("TransactionId")]
    public Transaction? Transaction { get; set; }

    [Column("wallet_id")]
    public Guid WalletId { get; set; }

    [ForeignKey("WalletId")]
    public Wallet? Wallet { get; set; }

    [Column("amount")]
    public decimal Amount { get; set; } // Negative for debit, positive for credit

    [Column("entry_type")]
    public string EntryType { get; set; } = string.Empty; // DEBIT, CREDIT

    [Column("balance_after")]
    public decimal BalanceAfter { get; set; }

    [Column("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}
