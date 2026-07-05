using System.ComponentModel.DataAnnotations.Schema;

namespace DotnetApi.Models;

[Table("transaction_transaction")]
public class Transaction
{
    [Column("id")]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Column("reference")]
    public string Reference { get; set; } = string.Empty;

    [Column("transaction_type")]
    public string TransactionType { get; set; } = string.Empty; // DEPOSIT, WITHDRAWAL, TRANSFER

    [Column("amount")]
    public decimal Amount { get; set; }

    [Column("currency")]
    public string Currency { get; set; } = "NGN";

    [Column("status")]
    public string Status { get; set; } = "PENDING"; // PENDING, SUCCESS, FAILED

    [Column("description")]
    public string? Description { get; set; }

    [Column("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public List<LedgerEntry> LedgerEntries { get; set; } = [];
}
