from __future__ import annotations

from typing import Optional, List, Annotated
from datetime import datetime, date

from fastapi import FastAPI, Depends, HTTPException, Query, Path, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
import jwt

app = FastAPI(title="Portfolio API", version="1.0.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ----- Schemas -----

class PortfolioBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class PortfolioResponse(PortfolioBase):
    id: int
    user_id: str
    total_value: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HoldingBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=100)
    shares: float = Field(..., gt=0)
    cost_basis: float = Field(..., gt=0)
    current_price: float = Field(..., gt=0)


class HoldingCreate(HoldingBase):
    pass


class HoldingUpdate(BaseModel):
    shares: Optional[float] = Field(default=None, gt=0)
    cost_basis: Optional[float] = Field(default=None, gt=0)
    current_price: Optional[float] = Field(default=None, gt=0)


class HoldingResponse(HoldingBase):
    id: int
    portfolio_id: int
    current_value: float
    gain_loss: float
    gain_loss_percent: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    transaction_type: str = Field(..., pattern="^(buy|sell|dividend)$")
    shares: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    transaction_date: date


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    id: int
    holding_id: int
    total: float
    created_at: datetime

    class Config:
        from_attributes = True


class PagedResponse(BaseModel):
    items: List
    total_count: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None


# ----- Dependencies -----

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, "secret", algorithms=["HS256"])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    except jwt.PyJWTError:
        raise credentials_exception


def get_portfolio_service() -> "PortfolioService":
    return PortfolioService()


def get_holding_service() -> "HoldingService":
    return HoldingService()


def get_transaction_service() -> "TransactionService":
    return TransactionService()


# ----- Routers -----

from fastapi import APIRouter

portfolio_router = APIRouter(prefix="/portfolios", tags=["portfolios"])
holding_router = APIRouter(prefix="/portfolios/{portfolio_id}/holdings", tags=["holdings"])
transaction_router = APIRouter(
    prefix="/portfolios/{portfolio_id}/holdings/{holding_id}/transactions",
    tags=["transactions"],
)


@portfolio_router.get("/", response_model=List[PortfolioResponse])
async def list_portfolios(
    current_user: Annotated[str, Depends(get_current_user)],
    service: Annotated["PortfolioService", Depends(get_portfolio_service)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> List[PortfolioResponse]:
    try:
        portfolios = await service.get_portfolios(user_id=current_user, skip=skip, limit=limit)
        return portfolios
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@portfolio_router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[str, Depends(get_current_user)],
    service: Annotated["PortfolioService", Depends(get_portfolio_service)],
) -> PortfolioResponse:
    try:
        portfolio = await service.get_portfolio(portfolio_id=portfolio_id, user_id=current_user)
        if portfolio is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
        return portfolio
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@portfolio_router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    body: PortfolioCreate,
    current_user: Annotated[str, Depends(get_current_user)],
    service: Annotated["PortfolioService", Depends(get_portfolio_service)],
) -> PortfolioResponse:
    try:
        portfolio = await service.create_portfolio(user_id=current_user, data=body)
        return portfolio
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@portfolio_router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: Annotated[int, Path(gt=0)],
    body: PortfolioUpdate,
    current_user: Annotated[str, Depends(get_current_user)],
    service: Annotated["PortfolioService", Depends(get_portfolio_service)],
) -> PortfolioResponse:
    try:
        portfolio = await service.update_portfolio(
            portfolio_id=portfolio_id, user_id=current_user, data=body
        )
        if portfolio is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
        return portfolio
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@portfolio_router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[str, Depends(get_current_user)],
    service: Annotated["PortfolioService", Depends(get_portfolio_service)],
) -> None:
    try:
        deleted = await service.delete_portfolio(portfolio_id=portfolio_id, user_id=current_user)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@holding_router.get("/", response_model=List[HoldingResponse])
async def list_holdings(
    portfolio_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[str, Depends(get_current_user)],
    service: Annotated["HoldingService", Depends(get_holding_service)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> List[HoldingResponse]:
    try:
        holdings = await service.get_holdings(
            portfolio_id=portfolio_id, user_id=current_user, skip=skip, limit=limit
        )
        return holdings
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@holding_router.post("/", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
async def create_holding(
    portfolio_id: Annotated[int, Path(gt=0)],
    body: HoldingCreate,
    current_user: Annotated[str, Depends(get_current_user)],
    service: Annotated["HoldingService", Depends(get_holding_service)],
) -> HoldingResponse:
    try:
        holding = await service.create_holding(
            portfolio_id=portfolio_id, user_id=current_user, data=body
        )
        return holding
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@transaction_router.get("/", response_model=List[TransactionResponse])
async def list_transactions(
    portfolio_id: Annotated[int, Path(gt=0)],
    holding_id: Annotated[int, Path(gt=0)],
    current_user: Annotated[str, Depends(get_current_user)],
    service: Annotated["TransactionService", Depends(get_transaction_service)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[TransactionResponse]:
    try:
        transactions = await service.get_transactions(
            holding_id=holding_id, user_id=current_user, skip=skip, limit=limit
        )
        return transactions
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@transaction_router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    portfolio_id: Annotated[int, Path(gt=0)],
    holding_id: Annotated[int, Path(gt=0)],
    body: TransactionCreate,
    current_user: Annotated[str, Depends(get_current_user)],
    service: Annotated["TransactionService", Depends(get_transaction_service)],
) -> TransactionResponse:
    try:
        transaction = await service.create_transaction(
            holding_id=holding_id, user_id=current_user, data=body
        )
        return transaction
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


app.include_router(portfolio_router)
app.include_router(holding_router)
app.include_router(transaction_router)


# ----- Stub service classes -----

class PortfolioService:
    async def get_portfolios(self, user_id: str, skip: int, limit: int) -> List[PortfolioResponse]:
        return []

    async def get_portfolio(self, portfolio_id: int, user_id: str) -> Optional[PortfolioResponse]:
        return None

    async def create_portfolio(self, user_id: str, data: PortfolioCreate) -> PortfolioResponse:
        raise NotImplementedError

    async def update_portfolio(self, portfolio_id: int, user_id: str, data: PortfolioUpdate) -> Optional[PortfolioResponse]:
        return None

    async def delete_portfolio(self, portfolio_id: int, user_id: str) -> bool:
        return False


class HoldingService:
    async def get_holdings(self, portfolio_id: int, user_id: str, skip: int, limit: int) -> List[HoldingResponse]:
        return []

    async def create_holding(self, portfolio_id: int, user_id: str, data: HoldingCreate) -> HoldingResponse:
        raise NotImplementedError


class TransactionService:
    async def get_transactions(self, holding_id: int, user_id: str, skip: int, limit: int) -> List[TransactionResponse]:
        return []

    async def create_transaction(self, holding_id: int, user_id: str, data: TransactionCreate) -> TransactionResponse:
        raise NotImplementedError
