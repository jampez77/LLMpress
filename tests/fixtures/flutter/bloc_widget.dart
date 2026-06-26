import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';

// Events
abstract class PortfolioActivityEvent extends Equatable {
  const PortfolioActivityEvent();

  @override
  List<Object?> get props => [];
}

class PortfolioActivityLoadRequested extends PortfolioActivityEvent {
  const PortfolioActivityLoadRequested({required this.userId});
  final String userId;

  @override
  List<Object?> get props => [userId];
}

class PortfolioActivityRefreshRequested extends PortfolioActivityEvent {
  const PortfolioActivityRefreshRequested({required this.userId});
  final String userId;

  @override
  List<Object?> get props => [userId];
}

class PortfolioActivityFilterChanged extends PortfolioActivityEvent {
  const PortfolioActivityFilterChanged({required this.filter});
  final ActivityFilter filter;

  @override
  List<Object?> get props => [filter];
}

// States
abstract class PortfolioActivityState extends Equatable {
  const PortfolioActivityState();

  @override
  List<Object?> get props => [];
}

class PortfolioActivityInitial extends PortfolioActivityState {
  const PortfolioActivityInitial();
}

class PortfolioActivityLoading extends PortfolioActivityState {
  const PortfolioActivityLoading();
}

class PortfolioActivityLoaded extends PortfolioActivityState {
  const PortfolioActivityLoaded({
    required this.activities,
    required this.filter,
    this.hasMore = true,
  });

  final List<ActivityItem> activities;
  final ActivityFilter filter;
  final bool hasMore;

  PortfolioActivityLoaded copyWith({
    List<ActivityItem>? activities,
    ActivityFilter? filter,
    bool? hasMore,
  }) {
    return PortfolioActivityLoaded(
      activities: activities ?? this.activities,
      filter: filter ?? this.filter,
      hasMore: hasMore ?? this.hasMore,
    );
  }

  @override
  List<Object?> get props => [activities, filter, hasMore];
}

class PortfolioActivityError extends PortfolioActivityState {
  const PortfolioActivityError({required this.message});
  final String message;

  @override
  List<Object?> get props => [message];
}

// BLoC
class PortfolioActivityBloc
    extends Bloc<PortfolioActivityEvent, PortfolioActivityState> {
  PortfolioActivityBloc({required this.repository})
      : super(const PortfolioActivityInitial()) {
    on<PortfolioActivityLoadRequested>(_onLoadRequested);
    on<PortfolioActivityRefreshRequested>(_onRefreshRequested);
    on<PortfolioActivityFilterChanged>(_onFilterChanged);
  }

  final ActivityRepository repository;

  Future<void> _onLoadRequested(
    PortfolioActivityLoadRequested event,
    Emitter<PortfolioActivityState> emit,
  ) async {
    emit(const PortfolioActivityLoading());
    try {
      final activities = await repository.getActivities(userId: event.userId);
      emit(PortfolioActivityLoaded(
        activities: activities,
        filter: ActivityFilter.all,
      ));
    } catch (e) {
      emit(PortfolioActivityError(message: e.toString()));
    }
  }

  Future<void> _onRefreshRequested(
    PortfolioActivityRefreshRequested event,
    Emitter<PortfolioActivityState> emit,
  ) async {
    final currentState = state;
    if (currentState is PortfolioActivityLoaded) {
      emit(const PortfolioActivityLoading());
      try {
        final activities =
            await repository.getActivities(userId: event.userId);
        emit(PortfolioActivityLoaded(
          activities: activities,
          filter: currentState.filter,
        ));
      } catch (e) {
        emit(PortfolioActivityError(message: e.toString()));
      }
    }
  }

  Future<void> _onFilterChanged(
    PortfolioActivityFilterChanged event,
    Emitter<PortfolioActivityState> emit,
  ) async {
    final currentState = state;
    if (currentState is PortfolioActivityLoaded) {
      emit(currentState.copyWith(filter: event.filter));
    }
  }
}

// Screen widget
class PortfolioActivityScreen extends StatelessWidget {
  const PortfolioActivityScreen({super.key, required this.userId});

  final String userId;

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) => PortfolioActivityBloc(
        repository: context.read<ActivityRepository>(),
      )..add(PortfolioActivityLoadRequested(userId: userId)),
      child: const PortfolioActivityView(),
    );
  }
}

class PortfolioActivityView extends StatelessWidget {
  const PortfolioActivityView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Portfolio Activity'),
        actions: [
          BlocBuilder<PortfolioActivityBloc, PortfolioActivityState>(
            buildWhen: (previous, current) =>
                previous.runtimeType != current.runtimeType,
            builder: (context, state) {
              return IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: state is PortfolioActivityLoaded
                    ? () => context.read<PortfolioActivityBloc>().add(
                          PortfolioActivityRefreshRequested(
                            userId: 'currentUser',
                          ),
                        )
                    : null,
              );
            },
          ),
        ],
      ),
      body: BlocListener<PortfolioActivityBloc, PortfolioActivityState>(
        listener: (context, state) {
          if (state is PortfolioActivityError) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(state.message)),
            );
          }
        },
        child: BlocBuilder<PortfolioActivityBloc, PortfolioActivityState>(
          builder: (context, state) {
            if (state is PortfolioActivityLoading) {
              return const Center(child: CircularProgressIndicator());
            }
            if (state is PortfolioActivityError) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(state.message),
                    ElevatedButton(
                      onPressed: () =>
                          context.read<PortfolioActivityBloc>().add(
                                const PortfolioActivityLoadRequested(
                                    userId: 'currentUser'),
                              ),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              );
            }
            if (state is PortfolioActivityLoaded) {
              return Column(
                children: [
                  _FilterBar(
                    selectedFilter: state.filter,
                    onFilterChanged: (filter) =>
                        context.read<PortfolioActivityBloc>().add(
                              PortfolioActivityFilterChanged(filter: filter),
                            ),
                  ),
                  Expanded(
                    child: ListView.builder(
                      itemCount: state.activities.length,
                      itemBuilder: (context, index) {
                        final activity = state.activities[index];
                        return _ActivityTile(activity: activity);
                      },
                    ),
                  ),
                ],
              );
            }
            return const SizedBox.shrink();
          },
        ),
      ),
    );
  }
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({
    required this.selectedFilter,
    required this.onFilterChanged,
  });

  final ActivityFilter selectedFilter;
  final ValueChanged<ActivityFilter> onFilterChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: ActivityFilter.values
          .map(
            (filter) => FilterChip(
              label: Text(filter.label),
              selected: selectedFilter == filter,
              onSelected: (_) => onFilterChanged(filter),
            ),
          )
          .toList(),
    );
  }
}

class _ActivityTile extends StatelessWidget {
  const _ActivityTile({required this.activity});

  final ActivityItem activity;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      title: Text(activity.title),
      subtitle: Text(activity.description),
      trailing: Text(activity.formattedDate),
    );
  }
}

// Domain models
enum ActivityFilter {
  all('All'),
  purchases('Purchases'),
  sales('Sales'),
  dividends('Dividends');

  const ActivityFilter(this.label);
  final String label;
}

class ActivityItem {
  const ActivityItem({
    required this.id,
    required this.title,
    required this.description,
    required this.date,
    required this.type,
  });

  final String id;
  final String title;
  final String description;
  final DateTime date;
  final ActivityFilter type;

  String get formattedDate =>
      '${date.day}/${date.month}/${date.year}';
}

abstract class ActivityRepository {
  Future<List<ActivityItem>> getActivities({required String userId});
}
