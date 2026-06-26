package com.example.portfolio;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

// Entity
@Entity
@Table(name = "portfolio_holdings")
public class PortfolioHolding {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String userId;

    @Column(nullable = false, length = 10)
    private String symbol;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false, precision = 18, scale = 8)
    private BigDecimal shares;

    @Column(nullable = false, precision = 18, scale = 4)
    private BigDecimal costBasis;

    @Column(nullable = false, precision = 18, scale = 4)
    private BigDecimal currentPrice;

    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }

    // Getters and setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public BigDecimal getShares() { return shares; }
    public void setShares(BigDecimal shares) { this.shares = shares; }
    public BigDecimal getCostBasis() { return costBasis; }
    public void setCostBasis(BigDecimal costBasis) { this.costBasis = costBasis; }
    public BigDecimal getCurrentPrice() { return currentPrice; }
    public void setCurrentPrice(BigDecimal currentPrice) { this.currentPrice = currentPrice; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }

    public BigDecimal getCurrentValue() {
        return shares.multiply(currentPrice);
    }

    public BigDecimal getGainLoss() {
        return getCurrentValue().subtract(costBasis);
    }
}

// Repository interface
@Repository
public interface PortfolioHoldingRepository extends JpaRepository<PortfolioHolding, Long> {

    List<PortfolioHolding> findByUserId(String userId);

    Optional<PortfolioHolding> findByUserIdAndSymbol(String userId, String symbol);

    List<PortfolioHolding> findByUserIdOrderByCurrentPriceDesc(String userId);

    @Query("SELECT h FROM PortfolioHolding h WHERE h.userId = :userId AND h.shares > 0")
    List<PortfolioHolding> findActiveHoldingsByUserId(@Param("userId") String userId);

    @Query("SELECT SUM(h.shares * h.currentPrice) FROM PortfolioHolding h WHERE h.userId = :userId")
    Optional<BigDecimal> calculateTotalValueByUserId(@Param("userId") String userId);

    @Query("SELECT h FROM PortfolioHolding h WHERE h.userId = :userId AND h.symbol IN :symbols")
    List<PortfolioHolding> findByUserIdAndSymbolIn(
        @Param("userId") String userId,
        @Param("symbols") List<String> symbols
    );

    boolean existsByUserIdAndSymbol(String userId, String symbol);

    long countByUserId(String userId);

    void deleteByUserIdAndSymbol(String userId, String symbol);
}

// Custom exception classes
class PortfolioHoldingNotFoundException extends RuntimeException {
    public PortfolioHoldingNotFoundException(String message) {
        super(message);
    }
    public PortfolioHoldingNotFoundException(Long id) {
        super("Portfolio holding not found with id: " + id);
    }
    public PortfolioHoldingNotFoundException(String userId, String symbol) {
        super("Portfolio holding not found for user: " + userId + ", symbol: " + symbol);
    }
}

class DuplicateHoldingException extends RuntimeException {
    public DuplicateHoldingException(String userId, String symbol) {
        super("Holding already exists for user: " + userId + ", symbol: " + symbol);
    }
}

class InsufficientSharesException extends RuntimeException {
    public InsufficientSharesException(String symbol, BigDecimal requested, BigDecimal available) {
        super("Insufficient shares for " + symbol +
              ": requested " + requested + ", available " + available);
    }
}

// Service
@Service
@Transactional
public class PortfolioHoldingService {

    @Autowired
    private PortfolioHoldingRepository holdingRepository;

    @Transactional(readOnly = true)
    public List<PortfolioHolding> getHoldingsByUserId(String userId) {
        return holdingRepository.findByUserId(userId);
    }

    @Transactional(readOnly = true)
    public PortfolioHolding getHoldingById(Long id) {
        return holdingRepository.findById(id)
            .orElseThrow(() -> new PortfolioHoldingNotFoundException(id));
    }

    @Transactional(readOnly = true)
    public PortfolioHolding getHoldingByUserIdAndSymbol(String userId, String symbol) {
        return holdingRepository.findByUserIdAndSymbol(userId, symbol)
            .orElseThrow(() -> new PortfolioHoldingNotFoundException(userId, symbol));
    }

    @Transactional(readOnly = true)
    public Optional<BigDecimal> getTotalPortfolioValue(String userId) {
        return holdingRepository.calculateTotalValueByUserId(userId);
    }

    public PortfolioHolding createHolding(
        String userId,
        String symbol,
        String name,
        BigDecimal shares,
        BigDecimal costBasis,
        BigDecimal currentPrice
    ) {
        if (holdingRepository.existsByUserIdAndSymbol(userId, symbol)) {
            throw new DuplicateHoldingException(userId, symbol);
        }

        PortfolioHolding holding = new PortfolioHolding();
        holding.setUserId(userId);
        holding.setSymbol(symbol);
        holding.setName(name);
        holding.setShares(shares);
        holding.setCostBasis(costBasis);
        holding.setCurrentPrice(currentPrice);

        return holdingRepository.save(holding);
    }

    public PortfolioHolding addShares(Long holdingId, BigDecimal additionalShares, BigDecimal price) {
        PortfolioHolding holding = holdingRepository.findById(holdingId)
            .orElseThrow(() -> new PortfolioHoldingNotFoundException(holdingId));

        BigDecimal newShares = holding.getShares().add(additionalShares);
        BigDecimal purchaseCost = additionalShares.multiply(price);
        BigDecimal newCostBasis = holding.getCostBasis().add(purchaseCost);

        holding.setShares(newShares);
        holding.setCostBasis(newCostBasis);

        return holdingRepository.save(holding);
    }

    public PortfolioHolding removeShares(Long holdingId, BigDecimal sharesToRemove) {
        PortfolioHolding holding = holdingRepository.findById(holdingId)
            .orElseThrow(() -> new PortfolioHoldingNotFoundException(holdingId));

        if (holding.getShares().compareTo(sharesToRemove) < 0) {
            throw new InsufficientSharesException(
                holding.getSymbol(),
                sharesToRemove,
                holding.getShares()
            );
        }

        BigDecimal newShares = holding.getShares().subtract(sharesToRemove);
        holding.setShares(newShares);

        return holdingRepository.save(holding);
    }

    public PortfolioHolding updateCurrentPrice(Long holdingId, BigDecimal newPrice) {
        PortfolioHolding holding = holdingRepository.findById(holdingId)
            .orElseThrow(() -> new PortfolioHoldingNotFoundException(holdingId));

        holding.setCurrentPrice(newPrice);
        return holdingRepository.save(holding);
    }

    public void updatePricesForSymbols(List<String> symbols, java.util.Map<String, BigDecimal> prices) {
        for (String symbol : symbols) {
            BigDecimal newPrice = prices.get(symbol);
            if (newPrice == null) continue;

            List<PortfolioHolding> holdings =
                holdingRepository.findByUserIdAndSymbolIn("*", List.of(symbol));
            for (PortfolioHolding holding : holdings) {
                holding.setCurrentPrice(newPrice);
                holdingRepository.save(holding);
            }
        }
    }

    public void deleteHolding(Long holdingId) {
        if (!holdingRepository.existsById(holdingId)) {
            throw new PortfolioHoldingNotFoundException(holdingId);
        }
        holdingRepository.deleteById(holdingId);
    }

    public void deleteHoldingByUserIdAndSymbol(String userId, String symbol) {
        if (!holdingRepository.existsByUserIdAndSymbol(userId, symbol)) {
            throw new PortfolioHoldingNotFoundException(userId, symbol);
        }
        holdingRepository.deleteByUserIdAndSymbol(userId, symbol);
    }
}
