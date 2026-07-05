using System.ComponentModel.DataAnnotations.Schema;

namespace DotnetApi.Models;

[Table("wallet_wallet")]
public class Wallet
{
    [Column("id")]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Column("name")]
    public string Name { get; set; } = "Default Wallet";

    [Column("currency")]
    public string Currency { get; set; } = "NGN";

    [Column("balance")]
    public decimal Balance { get; set; } = 0.0000m;

    [Column("user_id")]
    public Guid UserId { get; set; }

    [ForeignKey("UserId")]
    public User? User { get; set; }

    [Column("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [Column("updated_at")]
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
}
