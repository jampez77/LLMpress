import 'dart:math';

// String extensions
extension StringExtensions on String {
  String get capitalized =>
      isEmpty ? this : '${this[0].toUpperCase()}${substring(1)}';

  String get titleCase => split(' ')
      .map((word) => word.capitalized)
      .join(' ');

  String get camelCase {
    final words = split(RegExp(r'[\s_-]+'));
    if (words.isEmpty) return this;
    return words[0].toLowerCase() +
        words.skip(1).map((w) => w.capitalized).join('');
  }

  String get snakeCase =>
      replaceAllMapped(RegExp(r'[A-Z]'), (m) => '_${m[0]!.toLowerCase()}')
          .replaceAll(RegExp(r'^_'), '');

  bool get isEmail =>
      RegExp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
          .hasMatch(this);

  bool get isPhoneNumber =>
      RegExp(r'^\+?[\d\s\-()]{7,15}$').hasMatch(this);

  bool get isUrl =>
      RegExp(r'^https?://[^\s/$.?#].[^\s]*$').hasMatch(this);

  bool get isBlank => trim().isEmpty;
  bool get isNotBlank => !isBlank;

  String truncate(int maxLength, {String suffix = '...'}) {
    if (length <= maxLength) return this;
    return '${substring(0, maxLength - suffix.length)}$suffix';
  }

  String? get nullIfEmpty => isEmpty ? null : this;
  String? get nullIfBlank => isBlank ? null : this;

  int? toIntOrNull() => int.tryParse(this);
  double? toDoubleOrNull() => double.tryParse(this);

  List<String> splitLines() => split('\n');

  String removeWhitespace() => replaceAll(RegExp(r'\s+'), '');

  String repeat(int times) => List.filled(times, this).join();
}

// DateTime extensions
extension DateTimeExtensions on DateTime {
  bool get isToday {
    final now = DateTime.now();
    return year == now.year && month == now.month && day == now.day;
  }

  bool get isYesterday {
    final yesterday = DateTime.now().subtract(const Duration(days: 1));
    return year == yesterday.year &&
        month == yesterday.month &&
        day == yesterday.day;
  }

  bool get isTomorrow {
    final tomorrow = DateTime.now().add(const Duration(days: 1));
    return year == tomorrow.year &&
        month == tomorrow.month &&
        day == tomorrow.day;
  }

  bool get isInPast => isBefore(DateTime.now());
  bool get isInFuture => isAfter(DateTime.now());

  DateTime get startOfDay => DateTime(year, month, day);
  DateTime get endOfDay =>
      DateTime(year, month, day, 23, 59, 59, 999, 999);

  DateTime get startOfWeek {
    final diff = weekday - DateTime.monday;
    return subtract(Duration(days: diff)).startOfDay;
  }

  DateTime get endOfWeek => startOfWeek.add(const Duration(days: 6)).endOfDay;

  DateTime get startOfMonth => DateTime(year, month, 1);
  DateTime get endOfMonth => DateTime(year, month + 1, 0).endOfDay;

  String toRelativeString() {
    final now = DateTime.now();
    final diff = now.difference(this);

    if (diff.inSeconds < 60) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    if (diff.inDays < 30) return '${(diff.inDays / 7).floor()}w ago';
    if (diff.inDays < 365) return '${(diff.inDays / 30).floor()}mo ago';
    return '${(diff.inDays / 365).floor()}y ago';
  }

  String toFormattedDate({String separator = '/'}) =>
      '$day$separator$month$separator$year';

  String toIso8601DateString() =>
      '${year.toString().padLeft(4, '0')}-${month.toString().padLeft(2, '0')}-${day.toString().padLeft(2, '0')}';

  bool isSameDayAs(DateTime other) =>
      year == other.year && month == other.month && day == other.day;

  int get daysInMonth => DateTime(year, month + 1, 0).day;
}

// num extensions
extension NumExtensions on num {
  bool get isPositive => this > 0;
  bool get isNegative => this < 0;
  bool get isZero => this == 0;

  double get percentage => this / 100;

  num clamp01() => clamp(0, 1);

  String toCompactString() {
    if (abs() >= 1e12) return '${(this / 1e12).toStringAsFixed(1)}T';
    if (abs() >= 1e9) return '${(this / 1e9).toStringAsFixed(1)}B';
    if (abs() >= 1e6) return '${(this / 1e6).toStringAsFixed(1)}M';
    if (abs() >= 1e3) return '${(this / 1e3).toStringAsFixed(1)}K';
    return toStringAsFixed(2);
  }

  String toCurrencyString({String symbol = '\$', int decimals = 2}) =>
      '$symbol${toStringAsFixed(decimals)}';

  String toPercentString({int decimals = 2}) =>
      '${toStringAsFixed(decimals)}%';

  double lerp(num other, double t) => this + (other - this) * t;
}

// List extensions
extension ListExtensions<T> on List<T> {
  T? get firstOrNull => isEmpty ? null : first;
  T? get lastOrNull => isEmpty ? null : last;

  T? firstWhereOrNull(bool Function(T element) test) {
    for (final element in this) {
      if (test(element)) return element;
    }
    return null;
  }

  List<T> whereNot(bool Function(T element) test) =>
      where((e) => !test(e)).toList();

  List<List<T>> chunked(int size) {
    final chunks = <List<T>>[];
    for (var i = 0; i < length; i += size) {
      chunks.add(sublist(i, min(i + size, length)));
    }
    return chunks;
  }

  List<T> distinctBy<K>(K Function(T element) keySelector) {
    final seen = <K>{};
    return where((e) => seen.add(keySelector(e))).toList();
  }

  Map<K, List<T>> groupBy<K>(K Function(T element) keySelector) {
    final map = <K, List<T>>{};
    for (final element in this) {
      map.putIfAbsent(keySelector(element), () => []).add(element);
    }
    return map;
  }

  List<T> sortedBy<K extends Comparable<K>>(K Function(T element) keySelector,
      {bool descending = false}) {
    final copy = [...this];
    copy.sort((a, b) {
      final cmp = keySelector(a).compareTo(keySelector(b));
      return descending ? -cmp : cmp;
    });
    return copy;
  }

  T? maxBy<K extends Comparable<K>>(K Function(T element) keySelector) {
    if (isEmpty) return null;
    return reduce((a, b) =>
        keySelector(a).compareTo(keySelector(b)) >= 0 ? a : b);
  }

  T? minBy<K extends Comparable<K>>(K Function(T element) keySelector) {
    if (isEmpty) return null;
    return reduce((a, b) =>
        keySelector(a).compareTo(keySelector(b)) <= 0 ? a : b);
  }

  List<R> mapIndexed<R>(R Function(int index, T element) transform) {
    final result = <R>[];
    for (var i = 0; i < length; i++) {
      result.add(transform(i, this[i]));
    }
    return result;
  }

  void forEachIndexed(void Function(int index, T element) action) {
    for (var i = 0; i < length; i++) {
      action(i, this[i]);
    }
  }
}

// Map extensions
extension MapExtensions<K, V> on Map<K, V> {
  Map<K, V> where(bool Function(K key, V value) test) {
    return Map.fromEntries(
      entries.where((e) => test(e.key, e.value)),
    );
  }

  Map<K2, V2> mapEntries<K2, V2>(
      MapEntry<K2, V2> Function(K key, V value) transform) {
    return Map.fromEntries(entries.map((e) => transform(e.key, e.value)));
  }

  V getOrDefault(K key, V defaultValue) => this[key] ?? defaultValue;

  Map<K, V> merge(Map<K, V> other,
      {V Function(V existing, V incoming)? onConflict}) {
    final result = Map<K, V>.from(this);
    for (final entry in other.entries) {
      if (result.containsKey(entry.key) && onConflict != null) {
        result[entry.key] = onConflict(result[entry.key] as V, entry.value);
      } else {
        result[entry.key] = entry.value;
      }
    }
    return result;
  }
}

// Future extensions
extension FutureExtensions<T> on Future<T> {
  Future<T?> get orNull => then<T?>((v) => v).catchError((_) => null);

  Future<R> mapValue<R>(R Function(T value) transform) =>
      then(transform);

  Future<T> withTimeout(Duration timeout, {T Function()? onTimeout}) {
    if (onTimeout != null) {
      return this.timeout(timeout, onTimeout: onTimeout);
    }
    return this.timeout(timeout);
  }
}

// Nullable extensions
extension NullableExtensions<T> on T? {
  T orElse(T defaultValue) => this ?? defaultValue;
  T orElseGet(T Function() supplier) => this ?? supplier();
  R? mapNullable<R>(R Function(T value) transform) =>
      this == null ? null : transform(this as T);
  bool get isNull => this == null;
  bool get isNotNull => this != null;
}
