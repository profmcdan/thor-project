using Microsoft.EntityFrameworkCore;
using DotnetApi.Data;
using DotnetApi.Models;

namespace DotnetApi.Services;

public class WalletServiceException : Exception
{
    public WalletServiceException(string message) : base(message) { }
}

public class InsufficientFundsException : WalletServiceException
{
    public InsufficientFundsException(string message) : base(message) { }
}

public class WalletNotFoundException : WalletServiceException
{
    public WalletNotFoundException(string message) : base(message) { }
}

public class TransactionException : WalletServiceException
{
    public TransactionException(string message) : base(message) { }
}

public interface IWalletService
{
    Task<Transaction> DepositAsync(Guid walletId, decimal amount, string reference, string? description = null);
    Task<Transaction> WithdrawAsync(Guid walletId, decimal amount, string reference, string? description = null);
    Task<Transaction> TransferAsync(Guid sourceWalletId, Guid destinationWalletId, decimal amount, string reference, string? description = null);
}

public class WalletService : IWalletService
{
    private readonly AppDbContext _context;

    public WalletService(AppDbContext context)
    {
        _context = context;
    }

    public async Task<Transaction> DepositAsync(Guid walletId, decimal amount, string reference, string? description = null)
    {
        if (amount <= 0)
            throw new ArgumentException("Deposit amount must be greater than zero.");

        using var transaction = await _context.Database.BeginTransactionAsync();
        try
        {
            // Lock the wallet row
            var wallets = await _context.Wallets
                .FromSqlRaw("SELECT * FROM wallet_wallet WHERE id = {0} FOR UPDATE", walletId)
                .ToListAsync();

            var wallet = wallets.FirstOrDefault();
            if (wallet == null)
                throw new WalletNotFoundException($"Wallet with ID {walletId} does not exist.");

            // Create Transaction record
            var txn = new Transaction
            {
                Reference = reference,
                TransactionType = "DEPOSIT",
                Amount = amount,
                Currency = wallet.Currency,
                Status = "SUCCESS",
                Description = description ?? "Wallet deposit",
                CreatedAt = DateTime.UtcNow
            };

            _context.Transactions.Add(txn);

            try
            {
                await _context.SaveChangesAsync();
            }
            catch (DbUpdateException ex) when (ex.InnerException?.Message.Contains("unique") == true || ex.InnerException?.Message.Contains("duplicate") == true)
            {
                throw new TransactionException($"Transaction with reference {reference} already exists.");
            }

            // Update balance
            wallet.Balance += amount;
            wallet.UpdatedAt = DateTime.UtcNow;

            // Create Ledger entry
            var ledger = new LedgerEntry
            {
                TransactionId = txn.Id,
                WalletId = wallet.Id,
                Amount = amount,
                EntryType = "CREDIT",
                BalanceAfter = wallet.Balance,
                CreatedAt = DateTime.UtcNow
            };

            _context.LedgerEntries.Add(ledger);
            await _context.SaveChangesAsync();

            await transaction.CommitAsync();
            return txn;
        }
        catch
        {
            await transaction.RollbackAsync();
            throw;
        }
    }

    public async Task<Transaction> WithdrawAsync(Guid walletId, decimal amount, string reference, string? description = null)
    {
        if (amount <= 0)
            throw new ArgumentException("Withdrawal amount must be greater than zero.");

        using var transaction = await _context.Database.BeginTransactionAsync();
        try
        {
            // Lock the wallet row
            var wallets = await _context.Wallets
                .FromSqlRaw("SELECT * FROM wallet_wallet WHERE id = {0} FOR UPDATE", walletId)
                .ToListAsync();

            var wallet = wallets.FirstOrDefault();
            if (wallet == null)
                throw new WalletNotFoundException($"Wallet with ID {walletId} does not exist.");

            if (wallet.Balance < amount)
                throw new InsufficientFundsException($"Insufficient funds in wallet {walletId}.");

            // Create Transaction record
            var txn = new Transaction
            {
                Reference = reference,
                TransactionType = "WITHDRAWAL",
                Amount = amount,
                Currency = wallet.Currency,
                Status = "SUCCESS",
                Description = description ?? "Wallet withdrawal",
                CreatedAt = DateTime.UtcNow
            };

            _context.Transactions.Add(txn);

            try
            {
                await _context.SaveChangesAsync();
            }
            catch (DbUpdateException ex) when (ex.InnerException?.Message.Contains("unique") == true || ex.InnerException?.Message.Contains("duplicate") == true)
            {
                throw new TransactionException($"Transaction with reference {reference} already exists.");
            }

            // Update balance
            wallet.Balance -= amount;
            wallet.UpdatedAt = DateTime.UtcNow;

            // Create Ledger entry
            var ledger = new LedgerEntry
            {
                TransactionId = txn.Id,
                WalletId = wallet.Id,
                Amount = -amount,
                EntryType = "DEBIT",
                BalanceAfter = wallet.Balance,
                CreatedAt = DateTime.UtcNow
            };

            _context.LedgerEntries.Add(ledger);
            await _context.SaveChangesAsync();

            await transaction.CommitAsync();
            return txn;
        }
        catch
        {
            await transaction.RollbackAsync();
            throw;
        }
    }

    public async Task<Transaction> TransferAsync(Guid sourceWalletId, Guid destinationWalletId, decimal amount, string reference, string? description = null)
    {
        if (sourceWalletId == destinationWalletId)
            throw new ArgumentException("Cannot transfer to the same wallet.");

        if (amount <= 0)
            throw new ArgumentException("Transfer amount must be greater than zero.");

        // Sort the IDs for deterministic locking order
        var sortedIds = new List<Guid> { sourceWalletId, destinationWalletId };
        sortedIds.Sort();

        using var transaction = await _context.Database.BeginTransactionAsync();
        try
        {
            // Acquire locks in sorted order
            var lockedWallets = await _context.Wallets
                .FromSqlRaw("SELECT * FROM wallet_wallet WHERE id IN ({0}, {1}) ORDER BY id FOR UPDATE", sortedIds[0], sortedIds[1])
                .ToListAsync();

            if (lockedWallets.Count != 2)
                throw new WalletNotFoundException("One or both wallets could not be found.");

            var sourceWallet = lockedWallets.First(w => w.Id == sourceWalletId);
            var destWallet = lockedWallets.First(w => w.Id == destinationWalletId);

            if (sourceWallet.Currency != destWallet.Currency)
                throw new ArgumentException("Currency mismatch. Multi-currency transfers are not supported directly.");

            if (sourceWallet.Balance < amount)
                throw new InsufficientFundsException($"Insufficient funds in source wallet {sourceWalletId}.");

            // Create Transaction record
            var txn = new Transaction
            {
                Reference = reference,
                TransactionType = "TRANSFER",
                Amount = amount,
                Currency = sourceWallet.Currency,
                Status = "SUCCESS",
                Description = description ?? "Wallet-to-wallet transfer",
                CreatedAt = DateTime.UtcNow
            };

            _context.Transactions.Add(txn);

            try
            {
                await _context.SaveChangesAsync();
            }
            catch (DbUpdateException ex) when (ex.InnerException?.Message.Contains("unique") == true || ex.InnerException?.Message.Contains("duplicate") == true)
            {
                throw new TransactionException($"Transaction with reference {reference} already exists.");
            }

            // Update balances
            sourceWallet.Balance -= amount;
            sourceWallet.UpdatedAt = DateTime.UtcNow;

            destWallet.Balance += amount;
            destWallet.UpdatedAt = DateTime.UtcNow;

            // Create Ledger entries
            var sourceLedger = new LedgerEntry
            {
                TransactionId = txn.Id,
                WalletId = sourceWallet.Id,
                Amount = -amount,
                EntryType = "DEBIT",
                BalanceAfter = sourceWallet.Balance,
                CreatedAt = DateTime.UtcNow
            };

            var destLedger = new LedgerEntry
            {
                TransactionId = txn.Id,
                WalletId = destWallet.Id,
                Amount = amount,
                EntryType = "CREDIT",
                BalanceAfter = destWallet.Balance,
                CreatedAt = DateTime.UtcNow
            };

            _context.LedgerEntries.AddRange(sourceLedger, destLedger);
            await _context.SaveChangesAsync();

            await transaction.CommitAsync();
            return txn;
        }
        catch
        {
            await transaction.RollbackAsync();
            throw;
        }
    }
}
