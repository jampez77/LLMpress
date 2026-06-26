import 'package:dartz/dartz.dart';

// Failure types
abstract class Failure {
  const Failure({required this.message});
  final String message;
}

class NetworkFailure extends Failure {
  const NetworkFailure({required super.message});
}

class ServerFailure extends Failure {
  const ServerFailure({required super.message, this.statusCode});
  final int? statusCode;
}

class CacheFailure extends Failure {
  const CacheFailure({required super.message});
}

class NotFoundFailure extends Failure {
  const NotFoundFailure({required super.message});
}

class UnauthorizedFailure extends Failure {
  const UnauthorizedFailure({required super.message});
}

// Abstract repository
abstract class PortfolioRepository {
  Future<Either<Failure, PortfolioSummary>> getPortfolioSummary({
    required String userId,
  });

  Future<Either<Failure, List<PortfolioHolding>>> getHoldings({
    required String userId,
    int? page,
    int? pageSize,
  });

  Future<Either<Failure, PortfolioHolding>> getHoldingById({
    required String userId,
    required String holdingId,
  });

  Future<Either<Failure, List<PortfolioTransaction>>> getTransactions({
    required String userId,
    required String holdingId,
  });

  Future<Either<Failure, PortfolioTransaction>> createTransaction({
    required String userId,
    required CreateTransactionRequest request,
  });

  Future<Either<Failure, Unit>> deleteTransaction({
    required String userId,
    required String transactionId,
  });

  Future<Either<Failure, List<PortfolioWatchlistItem>>> getWatchlist({
    required String userId,
  });

  Future<Either<Failure, PortfolioWatchlistItem>> addToWatchlist({
    required String userId,
    required String symbol,
  });

  Future<Either<Failure, Unit>> removeFromWatchlist({
    required String userId,
    required String symbol,
  });

  Future<Either<Failure, List<PortfolioAlert>>> getAlerts({
    required String userId,
  });

  Future<Either<Failure, PortfolioAlert>> createAlert({
    required String userId,
    required CreateAlertRequest request,
  });

  Future<Either<Failure, Unit>> deleteAlert({
    required String userId,
    required String alertId,
  });
}

// Concrete implementation
class PortfolioRepositoryImpl implements PortfolioRepository {
  const PortfolioRepositoryImpl({
    required this.remoteDataSource,
    required this.localDataSource,
    required this.networkInfo,
  });

  final PortfolioRemoteDataSource remoteDataSource;
  final PortfolioLocalDataSource localDataSource;
  final NetworkInfo networkInfo;

  @override
  Future<Either<Failure, PortfolioSummary>> getPortfolioSummary({
    required String userId,
  }) async {
    if (!await networkInfo.isConnected) {
      try {
        final cached = await localDataSource.getCachedSummary(userId: userId);
        return Right(cached);
      } catch (e) {
        return Left(CacheFailure(message: 'No cached data available'));
      }
    }
    try {
      final summary = await remoteDataSource.getPortfolioSummary(userId: userId);
      await localDataSource.cacheSummary(summary: summary, userId: userId);
      return Right(summary);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<PortfolioHolding>>> getHoldings({
    required String userId,
    int? page,
    int? pageSize,
  }) async {
    if (!await networkInfo.isConnected) {
      try {
        final cached =
            await localDataSource.getCachedHoldings(userId: userId);
        return Right(cached);
      } catch (e) {
        return Left(CacheFailure(message: 'No cached holdings available'));
      }
    }
    try {
      final holdings = await remoteDataSource.getHoldings(
        userId: userId,
        page: page,
        pageSize: pageSize,
      );
      await localDataSource.cacheHoldings(holdings: holdings, userId: userId);
      return Right(holdings);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, PortfolioHolding>> getHoldingById({
    required String userId,
    required String holdingId,
  }) async {
    if (!await networkInfo.isConnected) {
      return Left(NetworkFailure(message: 'No internet connection'));
    }
    try {
      final holding = await remoteDataSource.getHoldingById(
        userId: userId,
        holdingId: holdingId,
      );
      return Right(holding);
    } on NotFoundException catch (e) {
      return Left(NotFoundFailure(message: e.message));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<PortfolioTransaction>>> getTransactions({
    required String userId,
    required String holdingId,
  }) async {
    if (!await networkInfo.isConnected) {
      return Left(NetworkFailure(message: 'No internet connection'));
    }
    try {
      final transactions = await remoteDataSource.getTransactions(
        userId: userId,
        holdingId: holdingId,
      );
      return Right(transactions);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, PortfolioTransaction>> createTransaction({
    required String userId,
    required CreateTransactionRequest request,
  }) async {
    if (!await networkInfo.isConnected) {
      return Left(NetworkFailure(message: 'No internet connection'));
    }
    try {
      final transaction = await remoteDataSource.createTransaction(
        userId: userId,
        request: request,
      );
      return Right(transaction);
    } on UnauthorizedException catch (e) {
      return Left(UnauthorizedFailure(message: e.message));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Unit>> deleteTransaction({
    required String userId,
    required String transactionId,
  }) async {
    if (!await networkInfo.isConnected) {
      return Left(NetworkFailure(message: 'No internet connection'));
    }
    try {
      await remoteDataSource.deleteTransaction(
        userId: userId,
        transactionId: transactionId,
      );
      return const Right(unit);
    } on NotFoundException catch (e) {
      return Left(NotFoundFailure(message: e.message));
    } on UnauthorizedException catch (e) {
      return Left(UnauthorizedFailure(message: e.message));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<PortfolioWatchlistItem>>> getWatchlist({
    required String userId,
  }) async {
    if (!await networkInfo.isConnected) {
      try {
        final cached =
            await localDataSource.getCachedWatchlist(userId: userId);
        return Right(cached);
      } catch (e) {
        return Left(CacheFailure(message: 'No cached watchlist available'));
      }
    }
    try {
      final watchlist =
          await remoteDataSource.getWatchlist(userId: userId);
      await localDataSource.cacheWatchlist(
          watchlist: watchlist, userId: userId);
      return Right(watchlist);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, PortfolioWatchlistItem>> addToWatchlist({
    required String userId,
    required String symbol,
  }) async {
    if (!await networkInfo.isConnected) {
      return Left(NetworkFailure(message: 'No internet connection'));
    }
    try {
      final item = await remoteDataSource.addToWatchlist(
        userId: userId,
        symbol: symbol,
      );
      return Right(item);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Unit>> removeFromWatchlist({
    required String userId,
    required String symbol,
  }) async {
    if (!await networkInfo.isConnected) {
      return Left(NetworkFailure(message: 'No internet connection'));
    }
    try {
      await remoteDataSource.removeFromWatchlist(
        userId: userId,
        symbol: symbol,
      );
      return const Right(unit);
    } on NotFoundException catch (e) {
      return Left(NotFoundFailure(message: e.message));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<PortfolioAlert>>> getAlerts({
    required String userId,
  }) async {
    if (!await networkInfo.isConnected) {
      return Left(NetworkFailure(message: 'No internet connection'));
    }
    try {
      final alerts = await remoteDataSource.getAlerts(userId: userId);
      return Right(alerts);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, PortfolioAlert>> createAlert({
    required String userId,
    required CreateAlertRequest request,
  }) async {
    if (!await networkInfo.isConnected) {
      return Left(NetworkFailure(message: 'No internet connection'));
    }
    try {
      final alert = await remoteDataSource.createAlert(
        userId: userId,
        request: request,
      );
      return Right(alert);
    } on UnauthorizedException catch (e) {
      return Left(UnauthorizedFailure(message: e.message));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Unit>> deleteAlert({
    required String userId,
    required String alertId,
  }) async {
    if (!await networkInfo.isConnected) {
      return Left(NetworkFailure(message: 'No internet connection'));
    }
    try {
      await remoteDataSource.deleteAlert(userId: userId, alertId: alertId);
      return const Right(unit);
    } on NotFoundException catch (e) {
      return Left(NotFoundFailure(message: e.message));
    } on UnauthorizedException catch (e) {
      return Left(UnauthorizedFailure(message: e.message));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }
}

// Exceptions
class ServerException implements Exception {
  const ServerException({required this.message, this.statusCode});
  final String message;
  final int? statusCode;
}

class NetworkException implements Exception {
  const NetworkException({required this.message});
  final String message;
}

class NotFoundException implements Exception {
  const NotFoundException({required this.message});
  final String message;
}

class UnauthorizedException implements Exception {
  const UnauthorizedException({required this.message});
  final String message;
}

// Stub interfaces
abstract class NetworkInfo {
  Future<bool> get isConnected;
}

abstract class PortfolioRemoteDataSource {
  Future<PortfolioSummary> getPortfolioSummary({required String userId});
  Future<List<PortfolioHolding>> getHoldings({required String userId, int? page, int? pageSize});
  Future<PortfolioHolding> getHoldingById({required String userId, required String holdingId});
  Future<List<PortfolioTransaction>> getTransactions({required String userId, required String holdingId});
  Future<PortfolioTransaction> createTransaction({required String userId, required CreateTransactionRequest request});
  Future<void> deleteTransaction({required String userId, required String transactionId});
  Future<List<PortfolioWatchlistItem>> getWatchlist({required String userId});
  Future<PortfolioWatchlistItem> addToWatchlist({required String userId, required String symbol});
  Future<void> removeFromWatchlist({required String userId, required String symbol});
  Future<List<PortfolioAlert>> getAlerts({required String userId});
  Future<PortfolioAlert> createAlert({required String userId, required CreateAlertRequest request});
  Future<void> deleteAlert({required String userId, required String alertId});
}

abstract class PortfolioLocalDataSource {
  Future<PortfolioSummary> getCachedSummary({required String userId});
  Future<void> cacheSummary({required PortfolioSummary summary, required String userId});
  Future<List<PortfolioHolding>> getCachedHoldings({required String userId});
  Future<void> cacheHoldings({required List<PortfolioHolding> holdings, required String userId});
  Future<List<PortfolioWatchlistItem>> getCachedWatchlist({required String userId});
  Future<void> cacheWatchlist({required List<PortfolioWatchlistItem> watchlist, required String userId});
}

// Stub models referenced above (normally in separate files)
class PortfolioSummary {}
class PortfolioHolding {}
class PortfolioTransaction {}
class PortfolioWatchlistItem {}
class PortfolioAlert {}
class CreateTransactionRequest {}
class CreateAlertRequest {}
