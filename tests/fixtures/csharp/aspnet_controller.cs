using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.ComponentModel.DataAnnotations;

namespace Portfolio.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class PortfolioController : ControllerBase
{
    private readonly IPortfolioService _portfolioService;
    private readonly IHoldingService _holdingService;
    private readonly ITransactionService _transactionService;
    private readonly ILogger<PortfolioController> _logger;

    public PortfolioController(
        IPortfolioService portfolioService,
        IHoldingService holdingService,
        ITransactionService transactionService,
        ILogger<PortfolioController> logger)
    {
        _portfolioService = portfolioService;
        _holdingService = holdingService;
        _transactionService = transactionService;
        _logger = logger;
    }

    [HttpGet]
    [ProducesResponseType(typeof(IEnumerable<PortfolioDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetPortfolios()
    {
        try
        {
            var userId = User.GetUserId();
            var portfolios = await _portfolioService.GetPortfoliosAsync(userId);
            return Ok(portfolios);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving portfolios");
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = ex.Message });
        }
    }

    [HttpGet("{id:long}")]
    [ProducesResponseType(typeof(PortfolioDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetPortfolioById(long id)
    {
        try
        {
            var userId = User.GetUserId();
            var portfolio = await _portfolioService.GetPortfolioByIdAsync(id, userId);
            if (portfolio is null)
                return NotFound(new { message = $"Portfolio {id} not found" });
            return Ok(portfolio);
        }
        catch (UnauthorizedAccessException ex)
        {
            _logger.LogWarning(ex, "Unauthorized access to portfolio {Id}", id);
            return Forbid();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving portfolio {Id}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = ex.Message });
        }
    }

    [HttpPost]
    [ProducesResponseType(typeof(PortfolioDto), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ValidationProblemDetails), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> CreatePortfolio([FromBody] CreatePortfolioRequest request)
    {
        if (!ModelState.IsValid)
            return ValidationProblem(ModelState);

        try
        {
            var userId = User.GetUserId();
            var portfolio = await _portfolioService.CreatePortfolioAsync(userId, request);
            return CreatedAtAction(nameof(GetPortfolioById), new { id = portfolio.Id }, portfolio);
        }
        catch (ArgumentException ex)
        {
            _logger.LogWarning(ex, "Invalid portfolio creation request");
            return BadRequest(new { message = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating portfolio");
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = ex.Message });
        }
    }

    [HttpPut("{id:long}")]
    [ProducesResponseType(typeof(PortfolioDto), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ValidationProblemDetails), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> UpdatePortfolio(long id, [FromBody] UpdatePortfolioRequest request)
    {
        if (!ModelState.IsValid)
            return ValidationProblem(ModelState);

        try
        {
            var userId = User.GetUserId();
            var portfolio = await _portfolioService.UpdatePortfolioAsync(id, userId, request);
            if (portfolio is null)
                return NotFound(new { message = $"Portfolio {id} not found" });
            return Ok(portfolio);
        }
        catch (UnauthorizedAccessException ex)
        {
            _logger.LogWarning(ex, "Unauthorized update attempt for portfolio {Id}", id);
            return Forbid();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error updating portfolio {Id}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = ex.Message });
        }
    }

    [HttpDelete("{id:long}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> DeletePortfolio(long id)
    {
        try
        {
            var userId = User.GetUserId();
            var deleted = await _portfolioService.DeletePortfolioAsync(id, userId);
            if (!deleted)
                return NotFound(new { message = $"Portfolio {id} not found" });
            return NoContent();
        }
        catch (UnauthorizedAccessException ex)
        {
            _logger.LogWarning(ex, "Unauthorized delete attempt for portfolio {Id}", id);
            return Forbid();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error deleting portfolio {Id}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = ex.Message });
        }
    }

    [HttpGet("{portfolioId:long}/holdings")]
    [ProducesResponseType(typeof(PagedResult<HoldingDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetHoldings(
        long portfolioId,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 20)
    {
        try
        {
            var userId = User.GetUserId();
            var holdings = await _holdingService.GetHoldingsAsync(portfolioId, userId, page, pageSize);
            return Ok(holdings);
        }
        catch (NotFoundException ex)
        {
            _logger.LogWarning(ex, "Portfolio {Id} not found", portfolioId);
            return NotFound(new { message = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving holdings for portfolio {Id}", portfolioId);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = ex.Message });
        }
    }

    [HttpGet("{portfolioId:long}/holdings/{holdingId:long}")]
    [ProducesResponseType(typeof(HoldingDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetHoldingById(long portfolioId, long holdingId)
    {
        try
        {
            var userId = User.GetUserId();
            var holding = await _holdingService.GetHoldingByIdAsync(portfolioId, holdingId, userId);
            if (holding is null)
                return NotFound(new { message = $"Holding {holdingId} not found" });
            return Ok(holding);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving holding {HoldingId}", holdingId);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = ex.Message });
        }
    }

    [HttpPost("{portfolioId:long}/holdings")]
    [ProducesResponseType(typeof(HoldingDto), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ValidationProblemDetails), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> CreateHolding(long portfolioId, [FromBody] CreateHoldingRequest request)
    {
        if (!ModelState.IsValid)
            return ValidationProblem(ModelState);

        try
        {
            var userId = User.GetUserId();
            var holding = await _holdingService.CreateHoldingAsync(portfolioId, userId, request);
            return CreatedAtAction(
                nameof(GetHoldingById),
                new { portfolioId, holdingId = holding.Id },
                holding);
        }
        catch (DuplicateException ex)
        {
            _logger.LogWarning(ex, "Duplicate holding in portfolio {Id}", portfolioId);
            return Conflict(new { message = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating holding in portfolio {Id}", portfolioId);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = ex.Message });
        }
    }

    [HttpDelete("{portfolioId:long}/holdings/{holdingId:long}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> DeleteHolding(long portfolioId, long holdingId)
    {
        try
        {
            var userId = User.GetUserId();
            var deleted = await _holdingService.DeleteHoldingAsync(portfolioId, holdingId, userId);
            if (!deleted)
                return NotFound(new { message = $"Holding {holdingId} not found" });
            return NoContent();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error deleting holding {HoldingId}", holdingId);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = ex.Message });
        }
    }

    [HttpGet("{portfolioId:long}/holdings/{holdingId:long}/transactions")]
    [ProducesResponseType(typeof(PagedResult<TransactionDto>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> GetTransactions(
        long portfolioId,
        long holdingId,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 50)
    {
        try
        {
            var userId = User.GetUserId();
            var transactions = await _transactionService.GetTransactionsAsync(
                holdingId, userId, page, pageSize);
            return Ok(transactions);
        }
        catch (NotFoundException ex)
        {
            _logger.LogWarning(ex, "Holding {Id} not found", holdingId);
            return NotFound(new { message = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving transactions for holding {Id}", holdingId);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = ex.Message });
        }
    }

    [HttpPost("{portfolioId:long}/holdings/{holdingId:long}/transactions")]
    [ProducesResponseType(typeof(TransactionDto), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ValidationProblemDetails), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<IActionResult> CreateTransaction(
        long portfolioId,
        long holdingId,
        [FromBody] CreateTransactionRequest request)
    {
        if (!ModelState.IsValid)
            return ValidationProblem(ModelState);

        try
        {
            var userId = User.GetUserId();
            var transaction = await _transactionService.CreateTransactionAsync(holdingId, userId, request);
            return CreatedAtAction(
                nameof(GetTransactions),
                new { portfolioId, holdingId },
                transaction);
        }
        catch (InsufficientSharesException ex)
        {
            _logger.LogWarning(ex, "Insufficient shares for transaction");
            return BadRequest(new { message = ex.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating transaction for holding {Id}", holdingId);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = ex.Message });
        }
    }
}

// DTOs
public record PortfolioDto(long Id, string Name, decimal TotalValue, DateTime CreatedAt);
public record HoldingDto(long Id, string Symbol, string Name, decimal Shares, decimal CurrentValue);
public record TransactionDto(long Id, string Type, decimal Shares, decimal Price, DateTime Date);
public record CreatePortfolioRequest([Required] string Name);
public record UpdatePortfolioRequest([Required] string Name);
public record CreateHoldingRequest([Required] string Symbol, [Required] string Name, decimal Shares, decimal Price);
public record CreateTransactionRequest([Required] string Type, decimal Shares, decimal Price, DateTime Date);
public record PagedResult<T>(IEnumerable<T> Items, int TotalCount, int Page, int PageSize);

// Exceptions
public class NotFoundException : Exception { public NotFoundException(string msg) : base(msg) { } }
public class DuplicateException : Exception { public DuplicateException(string msg) : base(msg) { } }
public class InsufficientSharesException : Exception { public InsufficientSharesException(string msg) : base(msg) { } }

// Service interfaces
public interface IPortfolioService
{
    Task<IEnumerable<PortfolioDto>> GetPortfoliosAsync(string userId);
    Task<PortfolioDto?> GetPortfolioByIdAsync(long id, string userId);
    Task<PortfolioDto> CreatePortfolioAsync(string userId, CreatePortfolioRequest request);
    Task<PortfolioDto?> UpdatePortfolioAsync(long id, string userId, UpdatePortfolioRequest request);
    Task<bool> DeletePortfolioAsync(long id, string userId);
}

public interface IHoldingService
{
    Task<PagedResult<HoldingDto>> GetHoldingsAsync(long portfolioId, string userId, int page, int pageSize);
    Task<HoldingDto?> GetHoldingByIdAsync(long portfolioId, long holdingId, string userId);
    Task<HoldingDto> CreateHoldingAsync(long portfolioId, string userId, CreateHoldingRequest request);
    Task<bool> DeleteHoldingAsync(long portfolioId, long holdingId, string userId);
}

public interface ITransactionService
{
    Task<PagedResult<TransactionDto>> GetTransactionsAsync(long holdingId, string userId, int page, int pageSize);
    Task<TransactionDto> CreateTransactionAsync(long holdingId, string userId, CreateTransactionRequest request);
}

// Extension method stub
public static class ClaimsPrincipalExtensions
{
    public static string GetUserId(this System.Security.Claims.ClaimsPrincipal principal)
        => principal.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
           ?? throw new UnauthorizedAccessException("User ID claim not found");
}
