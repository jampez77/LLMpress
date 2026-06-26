import 'package:freezed_annotation/freezed_annotation.dart';

part 'freezed_model.freezed.dart';
part 'freezed_model.g.dart';

// Portfolio summary model
@freezed
class PortfolioSummary with _$PortfolioSummary {
  const factory PortfolioSummary({
    required String portfolioId,
    required String portfolioName,
    required double portfolioTotalValue,
    required double portfolioDayChange,
    required double portfolioDayChangePercent,
    required double portfolioTotalGain,
    required double portfolioTotalGainPercent,
    required List<PortfolioHolding> portfolioHoldings,
    @Default(false) bool portfolioIsLoading,
    @Default(null) String? portfolioErrorMessage,
  }) = _PortfolioSummary;

  factory PortfolioSummary.fromJson(Map<String, dynamic> json) =>
      _$PortfolioSummaryFromJson(json);
}

// Portfolio holding model
@freezed
class PortfolioHolding with _$PortfolioHolding {
  const factory PortfolioHolding({
    required String portfolioHoldingId,
    required String portfolioHoldingSymbol,
    required String portfolioHoldingName,
    required double portfolioHoldingShares,
    required double portfolioHoldingCurrentPrice,
    required double portfolioHoldingCostBasis,
    required double portfolioHoldingCurrentValue,
    required double portfolioHoldingDayChange,
    required double portfolioHoldingDayChangePercent,
    required DateTime portfolioHoldingLastUpdated,
    @Default(HoldingStatus.active) HoldingStatus portfolioHoldingStatus,
    @Default([]) List<PortfolioTransaction> portfolioHoldingTransactions,
  }) = _PortfolioHolding;

  factory PortfolioHolding.fromJson(Map<String, dynamic> json) =>
      _$PortfolioHoldingFromJson(json);
}

// Portfolio transaction model
@freezed
class PortfolioTransaction with _$PortfolioTransaction {
  const factory PortfolioTransaction({
    required String portfolioTransactionId,
    required String portfolioTransactionSymbol,
    required double portfolioTransactionShares,
    required double portfolioTransactionPrice,
    required double portfolioTransactionTotal,
    required DateTime portfolioTransactionDate,
    required TransactionType portfolioTransactionType,
    @Default(null) String? portfolioTransactionNotes,
  }) = _PortfolioTransaction;

  factory PortfolioTransaction.fromJson(Map<String, dynamic> json) =>
      _$PortfolioTransactionFromJson(json);
}

// Portfolio watchlist item
@freezed
class PortfolioWatchlistItem with _$PortfolioWatchlistItem {
  const factory PortfolioWatchlistItem({
    required String portfolioWatchlistItemId,
    required String portfolioWatchlistItemSymbol,
    required String portfolioWatchlistItemName,
    required double portfolioWatchlistItemCurrentPrice,
    required double portfolioWatchlistItemDayChange,
    required double portfolioWatchlistItemDayChangePercent,
    required DateTime portfolioWatchlistItemAddedAt,
    @Default(null) double? portfolioWatchlistItemAlertPrice,
    @Default(false) bool portfolioWatchlistItemAlertEnabled,
  }) = _PortfolioWatchlistItem;

  factory PortfolioWatchlistItem.fromJson(Map<String, dynamic> json) =>
      _$PortfolioWatchlistItemFromJson(json);
}

// Portfolio alert model
@freezed
class PortfolioAlert with _$PortfolioAlert {
  const factory PortfolioAlert({
    required String portfolioAlertId,
    required String portfolioAlertSymbol,
    required double portfolioAlertTargetPrice,
    required AlertDirection portfolioAlertDirection,
    required DateTime portfolioAlertCreatedAt,
    @Default(false) bool portfolioAlertIsTriggered,
    @Default(null) DateTime? portfolioAlertTriggeredAt,
    @Default(null) String? portfolioAlertMessage,
  }) = _PortfolioAlert;

  const PortfolioAlert._();

  bool get portfolioAlertIsActive => !portfolioAlertIsTriggered;

  factory PortfolioAlert.fromJson(Map<String, dynamic> json) =>
      _$PortfolioAlertFromJson(json);
}

// Portfolio user preferences
@freezed
class PortfolioUserPreferences with _$PortfolioUserPreferences {
  const factory PortfolioUserPreferences({
    required String portfolioUserPreferencesUserId,
    @Default('USD') String portfolioUserPreferencesCurrency,
    @Default(true) bool portfolioUserPreferencesShowPercentages,
    @Default(true) bool portfolioUserPreferencesShowDayChange,
    @Default(false) bool portfolioUserPreferencesDarkMode,
    @Default(SortOrder.byValue) SortOrder portfolioUserPreferencesSortOrder,
    @Default([]) List<String> portfolioUserPreferencesHiddenSymbols,
  }) = _PortfolioUserPreferences;

  factory PortfolioUserPreferences.fromJson(Map<String, dynamic> json) =>
      _$PortfolioUserPreferencesFromJson(json);
}

// Enums
enum HoldingStatus { active, closed, suspended }

enum TransactionType { buy, sell, dividend, split }

enum AlertDirection { above, below }

enum SortOrder { byValue, byGain, byGainPercent, alphabetical }
