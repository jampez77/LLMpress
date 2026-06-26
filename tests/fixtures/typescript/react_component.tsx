import React, {
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
  FC,
} from 'react';

// Types
interface PortfolioHolding {
  id: string;
  symbol: string;
  name: string;
  shares: number;
  currentPrice: number;
  costBasis: number;
  currentValue: number;
  dayChange: number;
  dayChangePercent: number;
}

interface PortfolioSummary {
  totalValue: number;
  dayChange: number;
  dayChangePercent: number;
  totalGain: number;
  totalGainPercent: number;
  holdings: PortfolioHolding[];
}

interface PortfolioFilter {
  sortBy: 'value' | 'gain' | 'symbol';
  sortDirection: 'asc' | 'desc';
  searchQuery: string;
  showOnlyProfitable: boolean;
}

interface PortfolioDashboardProps {
  userId: string;
  initialFilter?: Partial<PortfolioFilter>;
  onHoldingClick?: (holding: PortfolioHolding) => void;
  onError?: (error: Error) => void;
}

interface HoldingCardProps {
  holding: PortfolioHolding;
  isSelected: boolean;
  onClick: (holding: PortfolioHolding) => void;
}

interface SummaryCardProps {
  summary: PortfolioSummary;
  isLoading: boolean;
}

interface FilterBarProps {
  filter: PortfolioFilter;
  onFilterChange: (filter: Partial<PortfolioFilter>) => void;
  resultCount: number;
}

// Default values
const DEFAULT_FILTER: PortfolioFilter = {
  sortBy: 'value',
  sortDirection: 'desc',
  searchQuery: '',
  showOnlyProfitable: false,
};

// Sub-components
const HoldingCard: FC<HoldingCardProps> = ({ holding, isSelected, onClick }) => {
  const handleClick = useCallback(() => {
    onClick(holding);
  }, [holding, onClick]);

  const gainColor = useMemo(
    () => (holding.dayChangePercent >= 0 ? '#22c55e' : '#ef4444'),
    [holding.dayChangePercent]
  );

  return (
    <div
      className={`holding-card ${isSelected ? 'selected' : ''}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
    >
      <div className="holding-symbol">{holding.symbol}</div>
      <div className="holding-name">{holding.name}</div>
      <div className="holding-value">${holding.currentValue.toFixed(2)}</div>
      <div className="holding-change" style={{ color: gainColor }}>
        {holding.dayChangePercent >= 0 ? '+' : ''}
        {holding.dayChangePercent.toFixed(2)}%
      </div>
      <div className="holding-shares">{holding.shares} shares</div>
    </div>
  );
};

const SummaryCard: FC<SummaryCardProps> = ({ summary, isLoading }) => {
  const totalValueFormatted = useMemo(
    () => `$${summary.totalValue.toFixed(2)}`,
    [summary.totalValue]
  );

  const dayChangeFormatted = useMemo(
    () =>
      `${summary.dayChange >= 0 ? '+' : ''}$${summary.dayChange.toFixed(2)} (${summary.dayChangePercent.toFixed(2)}%)`,
    [summary.dayChange, summary.dayChangePercent]
  );

  if (isLoading) {
    return <div className="summary-card skeleton" />;
  }

  return (
    <div className="summary-card">
      <div className="summary-total-value">{totalValueFormatted}</div>
      <div
        className="summary-day-change"
        style={{ color: summary.dayChange >= 0 ? '#22c55e' : '#ef4444' }}
      >
        {dayChangeFormatted}
      </div>
      <div className="summary-total-gain">
        Total gain: ${summary.totalGain.toFixed(2)} ({summary.totalGainPercent.toFixed(2)}%)
      </div>
    </div>
  );
};

const FilterBar: FC<FilterBarProps> = ({ filter, onFilterChange, resultCount }) => {
  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onFilterChange({ searchQuery: e.target.value });
    },
    [onFilterChange]
  );

  const handleSortChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      onFilterChange({ sortBy: e.target.value as PortfolioFilter['sortBy'] });
    },
    [onFilterChange]
  );

  const handleToggleProfitable = useCallback(() => {
    onFilterChange({ showOnlyProfitable: !filter.showOnlyProfitable });
  }, [filter.showOnlyProfitable, onFilterChange]);

  return (
    <div className="filter-bar">
      <input
        type="text"
        value={filter.searchQuery}
        onChange={handleSearchChange}
        placeholder="Search holdings..."
        className="filter-search"
      />
      <select value={filter.sortBy} onChange={handleSortChange} className="filter-sort">
        <option value="value">Sort by Value</option>
        <option value="gain">Sort by Gain</option>
        <option value="symbol">Sort by Symbol</option>
      </select>
      <label className="filter-toggle">
        <input
          type="checkbox"
          checked={filter.showOnlyProfitable}
          onChange={handleToggleProfitable}
        />
        Profitable only
      </label>
      <span className="filter-count">{resultCount} holdings</span>
    </div>
  );
};

// Main component
const PortfolioDashboard: FC<PortfolioDashboardProps> = ({
  userId,
  initialFilter,
  onHoldingClick,
  onError,
}) => {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [selectedHoldingId, setSelectedHoldingId] = useState<string | null>(null);
  const [filter, setFilter] = useState<PortfolioFilter>({
    ...DEFAULT_FILTER,
    ...initialFilter,
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchPortfolio = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/portfolio/${userId}`, {
        signal: abortControllerRef.current.signal,
      });
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      const data: PortfolioSummary = await response.json();
      setSummary(data);
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        onError?.(error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [userId, onError]);

  useEffect(() => {
    fetchPortfolio();
    return () => {
      abortControllerRef.current?.abort();
    };
  }, [fetchPortfolio]);

  useEffect(() => {
    const interval = setInterval(fetchPortfolio, 30_000);
    return () => clearInterval(interval);
  }, [fetchPortfolio]);

  const filteredHoldings = useMemo(() => {
    if (!summary) return [];

    let holdings = [...summary.holdings];

    if (filter.searchQuery) {
      const q = filter.searchQuery.toLowerCase();
      holdings = holdings.filter(
        (h) =>
          h.symbol.toLowerCase().includes(q) ||
          h.name.toLowerCase().includes(q)
      );
    }

    if (filter.showOnlyProfitable) {
      holdings = holdings.filter((h) => h.dayChange > 0);
    }

    holdings.sort((a, b) => {
      let cmp = 0;
      if (filter.sortBy === 'value') cmp = a.currentValue - b.currentValue;
      else if (filter.sortBy === 'gain') cmp = a.dayChangePercent - b.dayChangePercent;
      else if (filter.sortBy === 'symbol') cmp = a.symbol.localeCompare(b.symbol);
      return filter.sortDirection === 'desc' ? -cmp : cmp;
    });

    return holdings;
  }, [summary, filter]);

  const handleHoldingClick = useCallback(
    (holding: PortfolioHolding) => {
      setSelectedHoldingId(holding.id);
      onHoldingClick?.(holding);
    },
    [onHoldingClick]
  );

  const handleFilterChange = useCallback((partial: Partial<PortfolioFilter>) => {
    setFilter((prev) => ({ ...prev, ...partial }));
  }, []);

  if (error) {
    return (
      <div className="portfolio-error">
        <p>{error.message}</p>
        <button onClick={fetchPortfolio}>Retry</button>
      </div>
    );
  }

  return (
    <div className="portfolio-dashboard">
      {summary && (
        <SummaryCard summary={summary} isLoading={isLoading} />
      )}
      <FilterBar
        filter={filter}
        onFilterChange={handleFilterChange}
        resultCount={filteredHoldings.length}
      />
      <div className="holdings-grid">
        {isLoading && !summary
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="holding-card skeleton" />
            ))
          : filteredHoldings.map((holding) => (
              <HoldingCard
                key={holding.id}
                holding={holding}
                isSelected={selectedHoldingId === holding.id}
                onClick={handleHoldingClick}
              />
            ))}
      </div>
    </div>
  );
};

export default PortfolioDashboard;
export type {
  PortfolioHolding,
  PortfolioSummary,
  PortfolioFilter,
  PortfolioDashboardProps,
};
