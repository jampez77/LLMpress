// API response wrapper
interface ApiResponse<T> {
  data: T;
  message: string;
  success: boolean;
  timestamp: string;
}

interface ApiErrorResponse {
  error: string;
  code: string;
  details?: Record<string, string[]>;
}

interface PaginatedApiResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    pageSize: number;
    totalCount: number;
    totalPages: number;
  };
}

// Domain types
interface Portfolio {
  id: string;
  userId: string;
  name: string;
  totalValue: number;
  createdAt: string;
  updatedAt: string;
}

interface Holding {
  id: string;
  portfolioId: string;
  symbol: string;
  shares: number;
  costBasis: number;
  currentValue: number;
}

interface Transaction {
  id: string;
  holdingId: string;
  type: 'buy' | 'sell' | 'dividend';
  shares: number;
  price: number;
  total: number;
  date: string;
}

interface CreateTransactionDto {
  holdingId: string;
  type: 'buy' | 'sell' | 'dividend';
  shares: number;
  price: number;
  date: string;
}

interface UpdateHoldingDto {
  shares?: number;
  costBasis?: number;
}

// Custom error classes
class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly statusCode: number,
    public readonly details?: Record<string, string[]>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class NetworkError extends Error {
  constructor(message: string, public readonly cause?: Error) {
    super(message);
    this.name = 'NetworkError';
  }
}

// HTTP client wrapper
class HttpClient {
  constructor(
    private readonly baseUrl: string,
    private readonly getAuthToken: () => Promise<string>
  ) {}

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    let token: string;
    try {
      token = await this.getAuthToken();
    } catch (error) {
      throw new NetworkError('Failed to get auth token', error as Error);
    }

    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: body != null ? JSON.stringify(body) : undefined,
      });
    } catch (error) {
      throw new NetworkError('Network request failed', error as Error);
    }

    if (!response.ok) {
      let errorBody: ApiErrorResponse;
      try {
        errorBody = await response.json();
      } catch {
        throw new ApiError('UNKNOWN', response.statusText, response.status);
      }
      throw new ApiError(
        errorBody.code,
        errorBody.error,
        response.status,
        errorBody.details
      );
    }

    try {
      return (await response.json()) as T;
    } catch (error) {
      throw new NetworkError('Failed to parse response', error as Error);
    }
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path);
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>('POST', path, body);
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>('PUT', path, body);
  }

  async patch<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>('PATCH', path, body);
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>('DELETE', path);
  }
}

// Portfolio service
class PortfolioService {
  constructor(private readonly client: HttpClient) {}

  async getPortfolios(userId: string): Promise<ApiResponse<Portfolio[]>> {
    try {
      return await this.client.get<ApiResponse<Portfolio[]>>(
        `/users/${userId}/portfolios`
      );
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new NetworkError('Failed to fetch portfolios', error as Error);
    }
  }

  async getPortfolioById(
    userId: string,
    portfolioId: string
  ): Promise<ApiResponse<Portfolio>> {
    try {
      return await this.client.get<ApiResponse<Portfolio>>(
        `/users/${userId}/portfolios/${portfolioId}`
      );
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new NetworkError('Failed to fetch portfolio', error as Error);
    }
  }

  async createPortfolio(
    userId: string,
    name: string
  ): Promise<ApiResponse<Portfolio>> {
    try {
      return await this.client.post<ApiResponse<Portfolio>>(
        `/users/${userId}/portfolios`,
        { name }
      );
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new NetworkError('Failed to create portfolio', error as Error);
    }
  }

  async deletePortfolio(
    userId: string,
    portfolioId: string
  ): Promise<ApiResponse<void>> {
    try {
      return await this.client.delete<ApiResponse<void>>(
        `/users/${userId}/portfolios/${portfolioId}`
      );
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new NetworkError('Failed to delete portfolio', error as Error);
    }
  }

  async getHoldings(
    portfolioId: string,
    page = 1,
    pageSize = 20
  ): Promise<PaginatedApiResponse<Holding>> {
    try {
      return await this.client.get<PaginatedApiResponse<Holding>>(
        `/portfolios/${portfolioId}/holdings?page=${page}&pageSize=${pageSize}`
      );
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new NetworkError('Failed to fetch holdings', error as Error);
    }
  }

  async getHoldingById(
    portfolioId: string,
    holdingId: string
  ): Promise<ApiResponse<Holding>> {
    try {
      return await this.client.get<ApiResponse<Holding>>(
        `/portfolios/${portfolioId}/holdings/${holdingId}`
      );
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new NetworkError('Failed to fetch holding', error as Error);
    }
  }

  async updateHolding(
    portfolioId: string,
    holdingId: string,
    dto: UpdateHoldingDto
  ): Promise<ApiResponse<Holding>> {
    try {
      return await this.client.patch<ApiResponse<Holding>>(
        `/portfolios/${portfolioId}/holdings/${holdingId}`,
        dto
      );
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new NetworkError('Failed to update holding', error as Error);
    }
  }

  async deleteHolding(
    portfolioId: string,
    holdingId: string
  ): Promise<ApiResponse<void>> {
    try {
      return await this.client.delete<ApiResponse<void>>(
        `/portfolios/${portfolioId}/holdings/${holdingId}`
      );
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new NetworkError('Failed to delete holding', error as Error);
    }
  }

  async getTransactions(
    holdingId: string,
    page = 1,
    pageSize = 50
  ): Promise<PaginatedApiResponse<Transaction>> {
    try {
      return await this.client.get<PaginatedApiResponse<Transaction>>(
        `/holdings/${holdingId}/transactions?page=${page}&pageSize=${pageSize}`
      );
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new NetworkError('Failed to fetch transactions', error as Error);
    }
  }

  async createTransaction(
    dto: CreateTransactionDto
  ): Promise<ApiResponse<Transaction>> {
    try {
      return await this.client.post<ApiResponse<Transaction>>(
        `/holdings/${dto.holdingId}/transactions`,
        dto
      );
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new NetworkError('Failed to create transaction', error as Error);
    }
  }

  async deleteTransaction(
    holdingId: string,
    transactionId: string
  ): Promise<ApiResponse<void>> {
    try {
      return await this.client.delete<ApiResponse<void>>(
        `/holdings/${holdingId}/transactions/${transactionId}`
      );
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new NetworkError('Failed to delete transaction', error as Error);
    }
  }
}

export {
  PortfolioService,
  HttpClient,
  ApiError,
  NetworkError,
};

export type {
  ApiResponse,
  PaginatedApiResponse,
  Portfolio,
  Holding,
  Transaction,
  CreateTransactionDto,
  UpdateHoldingDto,
};
