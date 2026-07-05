using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using StackExchange.Redis;
using DotnetApi.Data;
using DotnetApi.DTOs;
using DotnetApi.Models;
using DotnetApi.Services;

namespace DotnetApi.Controllers;

[ApiController]
[Route("api")]
[Authorize]
public class TransactionController : BaseController
{
    private readonly AppDbContext _context;
    private readonly IWalletService _walletService;
    private readonly IConnectionMultiplexer _redis;

    public TransactionController(AppDbContext context, IWalletService walletService, IConnectionMultiplexer redis)
    {
        _context = context;
        _walletService = walletService;
        _redis = redis;
    }

    [HttpGet("wallets/{walletId:guid}/history")]
    public async Task<IActionResult> GetHistory(Guid walletId)
    {
        // Only allow users to view ledger entries for their own wallets
        var hasAccess = await _context.Wallets.AnyAsync(w => w.Id == walletId && w.UserId == CurrentUserId);
        if (!hasAccess)
        {
            return Forbid();
        }

        var entries = await _context.LedgerEntries
            .Include(l => l.Transaction)
            .Where(l => l.WalletId == walletId)
            .OrderByDescending(l => l.CreatedAt)
            .Select(l => new LedgerEntryDto
            {
                Id = l.Id,
                Wallet = l.WalletId,
                Amount = l.Amount.ToString("F4"),
                EntryType = l.EntryType,
                BalanceAfter = l.BalanceAfter.ToString("F4"),
                CreatedAt = l.CreatedAt,
                Transaction = new TransactionDto
                {
                    Id = l.Transaction!.Id,
                    Reference = l.Transaction.Reference,
                    TransactionType = l.Transaction.TransactionType,
                    Amount = l.Transaction.Amount.ToString("F4"),
                    Currency = l.Transaction.Currency,
                    Status = l.Transaction.Status,
                    Description = l.Transaction.Description,
                    CreatedAt = l.Transaction.CreatedAt
                }
            })
            .ToListAsync();

        return Ok(entries);
    }

    [HttpPost("transactions/deposit")]
    public async Task<IActionResult> Deposit([FromBody] DepositRequest request)
    {
        return await HandleIdempotentTransactionAsync(async (refKey) =>
        {
            // Validate wallet ownership
            var wallet = await _context.Wallets.AnyAsync(w => w.Id == request.WalletId && w.UserId == CurrentUserId);
            if (!wallet)
                throw new WalletNotFoundException("Wallet not found or does not belong to you.");

            return await _walletService.DepositAsync(request.WalletId, request.Amount, refKey, request.Description);
        });
    }

    [HttpPost("transactions/withdraw")]
    public async Task<IActionResult> Withdraw([FromBody] WithdrawRequest request)
    {
        return await HandleIdempotentTransactionAsync(async (refKey) =>
        {
            // Validate wallet ownership
            var wallet = await _context.Wallets.AnyAsync(w => w.Id == request.WalletId && w.UserId == CurrentUserId);
            if (!wallet)
                throw new WalletNotFoundException("Wallet not found or does not belong to you.");

            return await _walletService.WithdrawAsync(request.WalletId, request.Amount, refKey, request.Description);
        });
    }

    [HttpPost("transactions/transfer")]
    public async Task<IActionResult> Transfer([FromBody] TransferRequest request)
    {
        return await HandleIdempotentTransactionAsync(async (refKey) =>
        {
            if (request.SourceWalletId == request.DestinationWalletId)
                throw new ArgumentException("Source and destination wallets must be different.");

            // Validate source wallet ownership
            var sourceWallet = await _context.Wallets.FirstOrDefaultAsync(w => w.Id == request.SourceWalletId && w.UserId == CurrentUserId);
            if (sourceWallet == null)
                throw new WalletNotFoundException("Source wallet not found or does not belong to you.");

            // Validate destination wallet existence
            var destWallet = await _context.Wallets.FirstOrDefaultAsync(w => w.Id == request.DestinationWalletId);
            if (destWallet == null)
                throw new WalletNotFoundException("Destination wallet not found.");

            if (sourceWallet.Currency != destWallet.Currency)
                throw new ArgumentException("Transfers can only be made between wallets of the same currency.");

            if (sourceWallet.Balance < request.Amount)
                throw new InsufficientFundsException("Insufficient funds in source wallet.");

            return await _walletService.TransferAsync(request.SourceWalletId, request.DestinationWalletId, request.Amount, refKey, request.Description);
        });
    }

    private async Task<IActionResult> HandleIdempotentTransactionAsync(Func<string, Task<Transaction>> action)
    {
        var idempotencyKey = Request.Headers["X-Idempotency-Key"].ToString();
        if (string.IsNullOrWhiteSpace(idempotencyKey))
        {
            return BadRequest(new { error = "X-Idempotency-Key HTTP header is required for transaction endpoints." });
        }

        idempotencyKey = idempotencyKey.Trim();

        // 1. Check if transaction reference already exists in DB
        var existingTxn = await _context.Transactions.FirstOrDefaultAsync(t => t.Reference == idempotencyKey);
        if (existingTxn != null)
        {
            Response.Headers.Append("X-Cache-Lookup", "HIT");
            return Ok(MapToDto(existingTxn));
        }

        // 2. Acquire Redis distributed lock
        var redisDb = _redis.GetDatabase();
        var lockKey = $"lock:idempotency:{idempotencyKey}";
        
        var acquired = await redisDb.StringSetAsync(lockKey, "processing", TimeSpan.FromSeconds(30), When.NotExists);
        if (!acquired)
        {
            return StatusCode(409, new { error = "A duplicate request is currently being processed. Please retry in a few seconds." });
        }

        try
        {
            // 3. Execute transaction
            var txn = await action(idempotencyKey);
            return StatusCode(201, MapToDto(txn));
        }
        catch (WalletNotFoundException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        catch (InsufficientFundsException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        catch (TransactionException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        finally
        {
            // 4. Release lock
            await redisDb.KeyDeleteAsync(lockKey);
        }
    }

    private static TransactionDto MapToDto(Transaction txn)
    {
        return new TransactionDto
        {
            Id = txn.Id,
            Reference = txn.Reference,
            TransactionType = txn.TransactionType,
            Amount = txn.Amount.ToString("F4"),
            Currency = txn.Currency,
            Status = txn.Status,
            Description = txn.Description,
            CreatedAt = txn.CreatedAt
        };
    }
}
