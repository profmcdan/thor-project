using Microsoft.EntityFrameworkCore;
using DotnetApi.Models;

namespace DotnetApi.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
    {
    }

    public DbSet<User> Users { get; set; } = null!;
    public DbSet<Wallet> Wallets { get; set; } = null!;
    public DbSet<Transaction> Transactions { get; set; } = null!;
    public DbSet<LedgerEntry> LedgerEntries { get; set; } = null!;

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Map User
        modelBuilder.Entity<User>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.HasIndex(e => e.Email).IsUnique();
        });

        // Map Wallet
        modelBuilder.Entity<Wallet>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.HasIndex(e => new { e.UserId, e.Currency, e.Name }).IsUnique();
            
            // Precision for Decimal Fields (20, 4)
            entity.Property(e => e.Balance).HasPrecision(20, 4);
        });

        // Map Transaction
        modelBuilder.Entity<Transaction>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.HasIndex(e => e.Reference).IsUnique();
            entity.Property(e => e.Amount).HasPrecision(20, 4);
        });

        // Map LedgerEntry
        modelBuilder.Entity<LedgerEntry>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Amount).HasPrecision(20, 4);
            entity.Property(e => e.BalanceAfter).HasPrecision(20, 4);
        });
    }
}
