import 'dart:math';

// Generic result wrapper
class Result<T> {
  const Result._({this.value, this.error});

  final T? value;
  final Object? error;

  bool get isSuccess => error == null;
  bool get isFailure => error != null;

  factory Result.success(T value) => Result._(value: value);
  factory Result.failure(Object error) => Result._(error: error);

  R fold<R>(R Function(Object error) onFailure, R Function(T value) onSuccess) {
    if (isFailure) return onFailure(error!);
    return onSuccess(value as T);
  }

  Result<R> map<R>(R Function(T value) transform) {
    if (isFailure) return Result.failure(error!);
    return Result.success(transform(value as T));
  }

  Result<R> flatMap<R>(Result<R> Function(T value) transform) {
    if (isFailure) return Result.failure(error!);
    return transform(value as T);
  }
}

// Generic paginated response
class PaginatedResponse<T extends Identifiable> {
  const PaginatedResponse({
    required this.items,
    required this.totalCount,
    required this.page,
    required this.pageSize,
  });

  final List<T> items;
  final int totalCount;
  final int page;
  final int pageSize;

  bool get hasNextPage => (page * pageSize) < totalCount;
  bool get hasPreviousPage => page > 1;

  PaginatedResponse<R> mapItems<R extends Identifiable>(
      R Function(T item) transform) {
    return PaginatedResponse<R>(
      items: items.map(transform).toList(),
      totalCount: totalCount,
      page: page,
      pageSize: pageSize,
    );
  }
}

// Generic repository interface
abstract class Repository<T extends Identifiable, ID extends Comparable<ID>> {
  Future<Result<T>> findById(ID id);
  Future<Result<List<T>>> findAll({int page = 1, int pageSize = 20});
  Future<Result<T>> save(T entity);
  Future<Result<void>> delete(ID id);
  Future<Result<bool>> exists(ID id);
}

// Generic cache
class Cache<K extends Comparable<K>, V> {
  Cache({this.maxSize = 100, this.ttlSeconds = 300});

  final int maxSize;
  final int ttlSeconds;
  final Map<K, _CacheEntry<V>> _store = {};

  V? get(K key) {
    final entry = _store[key];
    if (entry == null) return null;
    if (entry.isExpired(ttlSeconds)) {
      _store.remove(key);
      return null;
    }
    return entry.value;
  }

  void put(K key, V value) {
    if (_store.length >= maxSize) {
      _evictOldest();
    }
    _store[key] = _CacheEntry<V>(value: value, createdAt: DateTime.now());
  }

  void invalidate(K key) => _store.remove(key);

  void clear() => _store.clear();

  void _evictOldest() {
    if (_store.isEmpty) return;
    final oldest = _store.entries
        .reduce((a, b) => a.value.createdAt.isBefore(b.value.createdAt) ? a : b);
    _store.remove(oldest.key);
  }
}

class _CacheEntry<V> {
  const _CacheEntry({required this.value, required this.createdAt});
  final V value;
  final DateTime createdAt;

  bool isExpired(int ttlSeconds) {
    return DateTime.now().difference(createdAt).inSeconds > ttlSeconds;
  }
}

// Generic sorted collection
class SortedList<T extends Comparable<T>> {
  SortedList({this.comparator});

  final Comparator<T>? comparator;
  final List<T> _items = [];

  List<T> get items => List.unmodifiable(_items);
  int get length => _items.length;
  bool get isEmpty => _items.isEmpty;

  void add(T item) {
    final index = _findInsertionIndex(item);
    _items.insert(index, item);
  }

  void addAll(Iterable<T> items) {
    for (final item in items) {
      add(item);
    }
  }

  bool remove(T item) => _items.remove(item);

  int _findInsertionIndex(T item) {
    int lo = 0, hi = _items.length;
    while (lo < hi) {
      final mid = (lo + hi) >> 1;
      final cmp = comparator != null
          ? comparator!(_items[mid], item)
          : _items[mid].compareTo(item);
      if (cmp <= 0) {
        lo = mid + 1;
      } else {
        hi = mid;
      }
    }
    return lo;
  }

  T? find(bool Function(T item) predicate) {
    for (final item in _items) {
      if (predicate(item)) return item;
    }
    return null;
  }
}

// Generic event bus
class EventBus<E extends AppEvent> {
  final Map<Type, List<Function>> _listeners = {};

  void on<T extends E>(void Function(T event) listener) {
    _listeners.putIfAbsent(T, () => []).add(listener);
  }

  void emit<T extends E>(T event) {
    final handlers = _listeners[T] ?? [];
    for (final handler in handlers) {
      (handler as void Function(T))(event);
    }
  }

  void off<T extends E>(void Function(T event) listener) {
    _listeners[T]?.remove(listener);
  }
}

// Generic state machine
class StateMachine<S extends Enum, E extends Enum> {
  StateMachine({required this.initialState});

  S initialState;
  late S _currentState = initialState;
  final Map<S, Map<E, S>> _transitions = {};
  final Map<S, void Function()> _onEnter = {};
  final Map<S, void Function()> _onExit = {};

  S get currentState => _currentState;

  void addTransition(S from, E event, S to) {
    _transitions.putIfAbsent(from, () => {})[event] = to;
  }

  void onEnter(S state, void Function() callback) {
    _onEnter[state] = callback;
  }

  void onExit(S state, void Function() callback) {
    _onExit[state] = callback;
  }

  bool dispatch(E event) {
    final nextState = _transitions[_currentState]?[event];
    if (nextState == null) return false;
    _onExit[_currentState]?.call();
    _currentState = nextState;
    _onEnter[_currentState]?.call();
    return true;
  }

  bool canDispatch(E event) =>
      _transitions[_currentState]?.containsKey(event) ?? false;
}

// Generic min/max heap
class MinHeap<T extends Comparable<T>> {
  final List<T> _heap = [];

  int get size => _heap.length;
  bool get isEmpty => _heap.isEmpty;

  T get min {
    if (_heap.isEmpty) throw StateError('Heap is empty');
    return _heap[0];
  }

  void insert(T value) {
    _heap.add(value);
    _siftUp(_heap.length - 1);
  }

  T extractMin() {
    if (_heap.isEmpty) throw StateError('Heap is empty');
    final min = _heap[0];
    final last = _heap.removeLast();
    if (_heap.isNotEmpty) {
      _heap[0] = last;
      _siftDown(0);
    }
    return min;
  }

  void _siftUp(int index) {
    while (index > 0) {
      final parent = (index - 1) ~/ 2;
      if (_heap[index].compareTo(_heap[parent]) < 0) {
        final tmp = _heap[index];
        _heap[index] = _heap[parent];
        _heap[parent] = tmp;
        index = parent;
      } else {
        break;
      }
    }
  }

  void _siftDown(int index) {
    final n = _heap.length;
    while (true) {
      int smallest = index;
      final left = 2 * index + 1;
      final right = 2 * index + 2;
      if (left < n && _heap[left].compareTo(_heap[smallest]) < 0) {
        smallest = left;
      }
      if (right < n && _heap[right].compareTo(_heap[smallest]) < 0) {
        smallest = right;
      }
      if (smallest == index) break;
      final tmp = _heap[index];
      _heap[index] = _heap[smallest];
      _heap[smallest] = tmp;
      index = smallest;
    }
  }
}

// Generic observable value
class Observable<T> {
  Observable(T initialValue) : _value = initialValue;

  T _value;
  final List<void Function(T oldValue, T newValue)> _observers = [];

  T get value => _value;

  set value(T newValue) {
    final old = _value;
    _value = newValue;
    for (final observer in _observers) {
      observer(old, newValue);
    }
  }

  void observe(void Function(T oldValue, T newValue) observer) {
    _observers.add(observer);
  }

  void unobserve(void Function(T oldValue, T newValue) observer) {
    _observers.remove(observer);
  }
}

// Marker interfaces
abstract class Identifiable {
  String get id;
}

abstract class AppEvent {}

// Type aliases
typedef Predicate<T> = bool Function(T value);
typedef Transformer<T, R> = R Function(T value);
typedef Comparator<T> = int Function(T a, T b);
typedef AsyncResult<T> = Future<Result<T>>;
typedef ResultList<T> = Result<List<T>>;
