from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any, ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator


# ----- Enums -----

class AssetClass(str, Enum):
    equity = "equity"
    fixed_income = "fixed_income"
    real_estate = "real_estate"
    commodity = "commodity"
    cash = "cash"
    crypto = "crypto"


class TransactionType(str, Enum):
    buy = "buy"
    sell = "sell"
    dividend = "dividend"
    split = "split"
    transfer = "transfer"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    very_high = "very_high"


# ----- Python dataclasses (mutable, no validation) -----

@dataclass
class PortfolioConfig:
    portfolio_id: str
    portfolio_name: str
    portfolio_owner_id: str
    portfolio_currency: str = "USD"
    portfolio_rebalance_threshold: float = 0.05
    portfolio_benchmark: Optional[str] = None
    portfolio_inception_date: Optional[date] = None
    portfolio_tags: List[str] = field(default_factory=list)
    portfolio_metadata: Dict[str, Any] = field(default_factory=dict)

    SUPPORTED_CURRENCIES: ClassVar[List[str]] = ["USD", "GBP", "EUR", "JPY", "CAD", "AUD"]

    def __post_init__(self) -> None:
        if self.portfolio_currency not in self.SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {self.portfolio_currency}")
        if self.portfolio_rebalance_threshold < 0 or self.portfolio_rebalance_threshold > 1:
            raise ValueError("Rebalance threshold must be between 0 and 1")


@dataclass
class HoldingSnapshot:
    holding_id: str
    holding_symbol: str
    holding_name: str
    holding_asset_class: AssetClass
    holding_shares: float
    holding_cost_basis: float
    holding_current_price: float
    holding_snapshot_date: date
    holding_currency: str = "USD"
    holding_sector: Optional[str] = None
    holding_country: Optional[str] = None
    holding_tags: List[str] = field(default_factory=list)

    @property
    def holding_current_value(self) -> float:
        return self.holding_shares * self.holding_current_price

    @property
    def holding_gain_loss(self) -> float:
        return self.holding_current_value - self.holding_cost_basis

    @property
    def holding_gain_loss_percent(self) -> float:
        if self.holding_cost_basis == 0:
            return 0.0
        return (self.holding_gain_loss / self.holding_cost_basis) * 100

    @property
    def holding_weight(self) -> float:
        return 0.0  # calculated externally


@dataclass
class TransactionRecord:
    transaction_id: str
    transaction_holding_id: str
    transaction_type: TransactionType
    transaction_shares: float
    transaction_price: float
    transaction_date: date
    transaction_currency: str = "USD"
    transaction_fees: float = 0.0
    transaction_notes: Optional[str] = None
    transaction_created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def transaction_total(self) -> float:
        return self.transaction_shares * self.transaction_price

    @property
    def transaction_net_total(self) -> float:
        return self.transaction_total + self.transaction_fees


# ----- Pydantic models (with validation) -----

class PortfolioSummaryModel(BaseModel):
    portfolio_id: str = Field(..., min_length=1)
    portfolio_name: str = Field(..., min_length=1, max_length=100)
    portfolio_owner_id: str = Field(..., min_length=1)
    portfolio_total_value: float = Field(..., ge=0)
    portfolio_total_cost: float = Field(..., ge=0)
    portfolio_day_change: float = Field(default=0.0)
    portfolio_day_change_percent: float = Field(default=0.0)
    portfolio_total_gain: float = Field(default=0.0)
    portfolio_total_gain_percent: float = Field(default=0.0)
    portfolio_currency: str = Field(default="USD")
    portfolio_last_updated: datetime = Field(default_factory=datetime.utcnow)
    portfolio_holdings_count: int = Field(default=0, ge=0)
    portfolio_asset_allocation: Dict[str, float] = Field(default_factory=dict)

    @field_validator("portfolio_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        allowed = {"USD", "GBP", "EUR", "JPY", "CAD", "AUD"}
        if v not in allowed:
            raise ValueError(f"Currency must be one of {allowed}")
        return v

    @field_validator("portfolio_day_change_percent", "portfolio_total_gain_percent")
    @classmethod
    def validate_percent(cls, v: float) -> float:
        if v < -100:
            raise ValueError("Percent cannot be less than -100")
        return round(v, 4)

    class Config:
        populate_by_name = True


class HoldingModel(BaseModel):
    holding_id: Optional[str] = Field(default=None)
    holding_portfolio_id: str = Field(..., min_length=1)
    holding_symbol: str = Field(..., min_length=1, max_length=10, pattern=r"^[A-Z0-9.]+$")
    holding_name: str = Field(..., min_length=1, max_length=100)
    holding_asset_class: AssetClass = Field(default=AssetClass.equity)
    holding_risk_level: RiskLevel = Field(default=RiskLevel.medium)
    holding_shares: float = Field(..., gt=0)
    holding_cost_basis: float = Field(..., ge=0)
    holding_current_price: float = Field(..., ge=0)
    holding_currency: str = Field(default="USD")
    holding_sector: Optional[str] = Field(default=None, max_length=50)
    holding_country: Optional[str] = Field(default=None, max_length=50)
    holding_isin: Optional[str] = Field(default=None)
    holding_notes: Optional[str] = Field(default=None, max_length=500)
    holding_created_at: datetime = Field(default_factory=datetime.utcnow)
    holding_updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("holding_symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("holding_isin")
    @classmethod
    def validate_isin(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        pattern = r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$"
        if not re.match(pattern, v):
            raise ValueError("Invalid ISIN format")
        return v

    @model_validator(mode="after")
    def validate_cost_basis_vs_shares(self) -> "HoldingModel":
        if self.holding_shares > 0 and self.holding_cost_basis < 0:
            raise ValueError("Cost basis cannot be negative when shares > 0")
        return self

    @property
    def holding_current_value(self) -> float:
        return self.holding_shares * self.holding_current_price

    @property
    def holding_gain_loss(self) -> float:
        return self.holding_current_value - self.holding_cost_basis

    class Config:
        populate_by_name = True


class TransactionModel(BaseModel):
    transaction_id: Optional[str] = Field(default=None)
    transaction_holding_id: str = Field(..., min_length=1)
    transaction_type: TransactionType
    transaction_shares: float = Field(..., gt=0)
    transaction_price: float = Field(..., ge=0)
    transaction_date: date
    transaction_fees: float = Field(default=0.0, ge=0)
    transaction_currency: str = Field(default="USD")
    transaction_exchange: Optional[str] = Field(default=None, max_length=50)
    transaction_notes: Optional[str] = Field(default=None, max_length=500)
    transaction_created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("transaction_date")
    @classmethod
    def validate_date_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Transaction date cannot be in the future")
        return v

    @field_validator("transaction_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        allowed = {"USD", "GBP", "EUR", "JPY", "CAD", "AUD"}
        if v not in allowed:
            raise ValueError(f"Currency must be one of {allowed}")
        return v

    @property
    def transaction_total(self) -> float:
        return self.transaction_shares * self.transaction_price

    @property
    def transaction_net_total(self) -> float:
        return self.transaction_total + self.transaction_fees

    class Config:
        populate_by_name = True


class WatchlistItemModel(BaseModel):
    watchlist_item_id: Optional[str] = Field(default=None)
    watchlist_item_user_id: str = Field(..., min_length=1)
    watchlist_item_symbol: str = Field(..., min_length=1, max_length=10)
    watchlist_item_name: str = Field(..., min_length=1, max_length=100)
    watchlist_item_current_price: float = Field(..., ge=0)
    watchlist_item_day_change: float = Field(default=0.0)
    watchlist_item_day_change_percent: float = Field(default=0.0)
    watchlist_item_alert_price: Optional[float] = Field(default=None, ge=0)
    watchlist_item_alert_enabled: bool = Field(default=False)
    watchlist_item_notes: Optional[str] = Field(default=None, max_length=500)
    watchlist_item_added_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("watchlist_item_symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().strip()

    @model_validator(mode="after")
    def validate_alert_config(self) -> "WatchlistItemModel":
        if self.watchlist_item_alert_enabled and self.watchlist_item_alert_price is None:
            raise ValueError("Alert price is required when alert is enabled")
        return self

    class Config:
        populate_by_name = True
