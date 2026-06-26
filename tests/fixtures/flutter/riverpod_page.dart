import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// State models
class PortfolioState {
  const PortfolioState({
    this.holdings = const [],
    this.totalValue = 0.0,
    this.isLoading = false,
    this.errorMessage,
  });

  final List<Holding> holdings;
  final double totalValue;
  final bool isLoading;
  final String? errorMessage;

  PortfolioState copyWith({
    List<Holding>? holdings,
    double? totalValue,
    bool? isLoading,
    String? errorMessage,
  }) {
    return PortfolioState(
      holdings: holdings ?? this.holdings,
      totalValue: totalValue ?? this.totalValue,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage ?? this.errorMessage,
    );
  }
}

// StateNotifier
class PortfolioNotifier extends StateNotifier<PortfolioState> {
  PortfolioNotifier(this._repository) : super(const PortfolioState());

  final PortfolioRepository _repository;

  Future<void> loadPortfolio(String userId) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final holdings = await _repository.getHoldings(userId: userId);
      final totalValue = holdings.fold<double>(
        0.0,
        (sum, h) => sum + h.currentValue,
      );
      state = state.copyWith(
        holdings: holdings,
        totalValue: totalValue,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  Future<void> refreshPortfolio(String userId) async {
    await loadPortfolio(userId);
  }
}

// Providers
final portfolioRepositoryProvider = Provider<PortfolioRepository>((ref) {
  return RemotePortfolioRepository();
});

final portfolioProvider =
    StateNotifierProvider<PortfolioNotifier, PortfolioState>((ref) {
  final repository = ref.watch(portfolioRepositoryProvider);
  return PortfolioNotifier(repository);
});

final holdingsProvider = Provider<AsyncValue<List<Holding>>>((ref) {
  final portfolioState = ref.watch(portfolioProvider);
  if (portfolioState.isLoading) return const AsyncValue.loading();
  if (portfolioState.errorMessage != null) {
    return AsyncValue.error(portfolioState.errorMessage!, StackTrace.empty);
  }
  return AsyncValue.data(portfolioState.holdings);
});

final totalValueProvider = Provider<double>((ref) {
  return ref.watch(portfolioProvider).totalValue;
});

final filteredHoldingsProvider =
    Provider.family<AsyncValue<List<Holding>>, HoldingFilter>((ref, filter) {
  final holdings = ref.watch(holdingsProvider);
  return holdings.whenData(
    (data) => data.where((h) => filter.matches(h)).toList(),
  );
});

// Page widget
class PortfolioPage extends ConsumerStatefulWidget {
  const PortfolioPage({super.key, required this.userId});

  final String userId;

  @override
  ConsumerState<PortfolioPage> createState() => _PortfolioPageState();
}

class _PortfolioPageState extends ConsumerState<PortfolioPage> {
  @override
  void initState() {
    super.initState();
    Future.microtask(
      () => ref
          .read(portfolioProvider.notifier)
          .loadPortfolio(widget.userId),
    );
  }

  @override
  Widget build(BuildContext context) {
    final portfolioState = ref.watch(portfolioProvider);
    final holdings = ref.watch(holdingsProvider);
    final totalValue = ref.watch(totalValueProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Portfolio'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref
                .read(portfolioProvider.notifier)
                .refreshPortfolio(widget.userId),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref
            .read(portfolioProvider.notifier)
            .refreshPortfolio(widget.userId),
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(
              child: _SummaryCard(totalValue: totalValue),
            ),
            holdings.when(
              data: (data) => SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) => _HoldingCard(holding: data[index]),
                  childCount: data.length,
                ),
              ),
              loading: () => const SliverFillRemaining(
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (error, stack) => SliverFillRemaining(
                child: Center(child: Text(error.toString())),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SummaryCard extends ConsumerWidget {
  const _SummaryCard({required this.totalValue});

  final double totalValue;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final portfolioState = ref.watch(portfolioProvider);
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Total Value', style: TextStyle(fontSize: 14)),
            Text(
              '\$${totalValue.toStringAsFixed(2)}',
              style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            ),
            if (portfolioState.isLoading)
              const LinearProgressIndicator(),
          ],
        ),
      ),
    );
  }
}

class _HoldingCard extends ConsumerWidget {
  const _HoldingCard({required this.holding});

  final Holding holding;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: ListTile(
        title: Text(holding.symbol),
        subtitle: Text(holding.name),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text('\$${holding.currentValue.toStringAsFixed(2)}'),
            Text(
              '${holding.gainLossPercent >= 0 ? '+' : ''}${holding.gainLossPercent.toStringAsFixed(2)}%',
              style: TextStyle(
                color: holding.gainLossPercent >= 0
                    ? Colors.green
                    : Colors.red,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// Domain models
class Holding {
  const Holding({
    required this.symbol,
    required this.name,
    required this.shares,
    required this.currentPrice,
    required this.costBasis,
  });

  final String symbol;
  final String name;
  final double shares;
  final double currentPrice;
  final double costBasis;

  double get currentValue => shares * currentPrice;
  double get gainLoss => currentValue - costBasis;
  double get gainLossPercent => (gainLoss / costBasis) * 100;
}

class HoldingFilter {
  const HoldingFilter({this.onlyProfitable = false});
  final bool onlyProfitable;

  bool matches(Holding holding) {
    if (onlyProfitable) return holding.gainLoss > 0;
    return true;
  }
}

abstract class PortfolioRepository {
  Future<List<Holding>> getHoldings({required String userId});
}

class RemotePortfolioRepository implements PortfolioRepository {
  @override
  Future<List<Holding>> getHoldings({required String userId}) async {
    await Future.delayed(const Duration(milliseconds: 800));
    return const [];
  }
}
