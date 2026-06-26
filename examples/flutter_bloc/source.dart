import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:dartz/dartz.dart';

// Domain layer
abstract class PortfolioRepository {
  Future<Either<PortfolioFailure, List<PortfolioItem>>> getPortfolioItems(String userId);
  Future<Either<PortfolioFailure, PortfolioItem>> getPortfolioItem(String itemId);
  Future<Either<PortfolioFailure, PortfolioItem>> updatePortfolioItem(PortfolioItem item);
  Future<Either<PortfolioFailure, bool>> deletePortfolioItem(String itemId);
  Future<Either<PortfolioFailure, List<PortfolioItem>>> refreshPortfolioItems(String userId);
}

// BLoC Events
abstract class PortfolioEvent {}

class LoadPortfolioItems extends PortfolioEvent {
  final String userId;
  LoadPortfolioItems(this.userId);
}

class RefreshPortfolioItems extends PortfolioEvent {
  final String userId;
  RefreshPortfolioItems(this.userId);
}

class UpdatePortfolioItem extends PortfolioEvent {
  final PortfolioItem item;
  UpdatePortfolioItem(this.item);
}

class DeletePortfolioItem extends PortfolioEvent {
  final String itemId;
  DeletePortfolioItem(this.itemId);
}

// BLoC States
abstract class PortfolioState {}

class PortfolioInitial extends PortfolioState {}

class PortfolioLoading extends PortfolioState {}

class PortfolioLoaded extends PortfolioState {
  final List<PortfolioItem> items;
  PortfolioLoaded(this.items);
}

class PortfolioItemUpdated extends PortfolioState {
  final PortfolioItem item;
  PortfolioItemUpdated(this.item);
}

class PortfolioItemDeleted extends PortfolioState {
  final String itemId;
  PortfolioItemDeleted(this.itemId);
}

class PortfolioError extends PortfolioState {
  final PortfolioFailure failure;
  PortfolioError(this.failure);
}

// BLoC
class PortfolioBloc extends Bloc<PortfolioEvent, PortfolioState> {
  final PortfolioRepository _portfolioRepository;

  PortfolioBloc({required PortfolioRepository portfolioRepository})
      : _portfolioRepository = portfolioRepository,
        super(PortfolioInitial()) {
    on<LoadPortfolioItems>(_onLoadPortfolioItems);
    on<RefreshPortfolioItems>(_onRefreshPortfolioItems);
    on<UpdatePortfolioItem>(_onUpdatePortfolioItem);
    on<DeletePortfolioItem>(_onDeletePortfolioItem);
  }

  Future<void> _onLoadPortfolioItems(
    LoadPortfolioItems event,
    Emitter<PortfolioState> emit,
  ) async {
    emit(PortfolioLoading());
    final Either<PortfolioFailure, List<PortfolioItem>> result =
        await _portfolioRepository.getPortfolioItems(event.userId);
    result.fold(
      (PortfolioFailure failure) => emit(PortfolioError(failure)),
      (List<PortfolioItem> items) => emit(PortfolioLoaded(items)),
    );
  }

  Future<void> _onRefreshPortfolioItems(
    RefreshPortfolioItems event,
    Emitter<PortfolioState> emit,
  ) async {
    emit(PortfolioLoading());
    final Either<PortfolioFailure, List<PortfolioItem>> result =
        await _portfolioRepository.refreshPortfolioItems(event.userId);
    result.fold(
      (PortfolioFailure failure) => emit(PortfolioError(failure)),
      (List<PortfolioItem> items) => emit(PortfolioLoaded(items)),
    );
  }

  Future<void> _onUpdatePortfolioItem(
    UpdatePortfolioItem event,
    Emitter<PortfolioState> emit,
  ) async {
    emit(PortfolioLoading());
    final Either<PortfolioFailure, PortfolioItem> result =
        await _portfolioRepository.updatePortfolioItem(event.item);
    result.fold(
      (PortfolioFailure failure) => emit(PortfolioError(failure)),
      (PortfolioItem item) => emit(PortfolioItemUpdated(item)),
    );
  }

  Future<void> _onDeletePortfolioItem(
    DeletePortfolioItem event,
    Emitter<PortfolioState> emit,
  ) async {
    emit(PortfolioLoading());
    final Either<PortfolioFailure, bool> result =
        await _portfolioRepository.deletePortfolioItem(event.itemId);
    result.fold(
      (PortfolioFailure failure) => emit(PortfolioError(failure)),
      (_) => emit(PortfolioItemDeleted(event.itemId)),
    );
  }
}

// Widget
class PortfolioPage extends StatelessWidget {
  final String userId;
  const PortfolioPage({Key? key, required this.userId}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) => PortfolioBloc(
        portfolioRepository: context.read<PortfolioRepository>(),
      )..add(LoadPortfolioItems(userId)),
      child: const PortfolioView(),
    );
  }
}

class PortfolioView extends StatelessWidget {
  const PortfolioView({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Portfolio')),
      body: BlocConsumer<PortfolioBloc, PortfolioState>(
        listener: (context, state) {
          if (state is PortfolioError) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(state.failure.message)),
            );
          }
        },
        builder: (context, state) {
          if (state is PortfolioLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          if (state is PortfolioLoaded) {
            return PortfolioItemList(items: state.items);
          }
          if (state is PortfolioError) {
            return Center(child: Text(state.failure.message));
          }
          return const SizedBox.shrink();
        },
      ),
    );
  }
}

class PortfolioItemList extends StatelessWidget {
  final List<PortfolioItem> items;
  const PortfolioItemList({Key? key, required this.items}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (context, index) {
        final PortfolioItem item = items[index];
        return PortfolioItemCard(
          item: item,
          onDelete: () => context.read<PortfolioBloc>().add(
            DeletePortfolioItem(item.id),
          ),
        );
      },
    );
  }
}
