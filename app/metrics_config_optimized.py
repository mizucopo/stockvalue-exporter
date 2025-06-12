"""最適化されたメトリクス設定の提案."""

# 統合後のメトリクス設定（43個 → 12個に削減）
OPTIMIZED_METRICS_CONFIG = {
    "gauges": [
        # 1. 統合価格メトリクス（4個の価格系メトリクスを1個に統合）
        {
            "name": "asset_price_current",
            "description": "Current asset price/rate/value",
            "labels": ["symbol", "name", "currency", "exchange", "asset_type"],
            "key": "asset_price",
        },
        # 2. 統合前日終値メトリクス
        {
            "name": "asset_previous_close",
            "description": "Previous day closing price/rate/value",
            "labels": ["symbol", "name", "exchange", "asset_type"],
            "key": "asset_previous_close",
        },
        # 3. 統合価格変動メトリクス
        {
            "name": "asset_price_change",
            "description": "Price/rate/value change from previous close",
            "labels": ["symbol", "name", "exchange", "asset_type"],
            "key": "asset_price_change",
        },
        # 4. 統合価格変動率メトリクス
        {
            "name": "asset_price_change_percent",
            "description": "Price/rate/value change percentage from previous close",
            "labels": ["symbol", "name", "exchange", "asset_type"],
            "key": "asset_price_change_percent",
        },
        # 5. 統合出来高メトリクス（為替以外）
        {
            "name": "asset_volume_current",
            "description": "Current asset volume",
            "labels": ["symbol", "name", "exchange", "asset_type"],
            "key": "asset_volume",
        },
        # 6. 統合時価総額メトリクス（株式・暗号通貨のみ）
        {
            "name": "asset_market_cap",
            "description": "Market capitalization",
            "labels": ["symbol", "name", "exchange", "asset_type"],
            "key": "asset_market_cap",
        },
        # 7. 統合52週高値メトリクス
        {
            "name": "asset_52week_high",
            "description": "52 week high price/rate/value",
            "labels": ["symbol", "name", "exchange", "asset_type"],
            "key": "asset_52week_high",
        },
        # 8. 統合52週安値メトリクス
        {
            "name": "asset_52week_low",
            "description": "52 week low price/rate/value",
            "labels": ["symbol", "name", "exchange", "asset_type"],
            "key": "asset_52week_low",
        },
        # 9. 統合更新タイムスタンプ
        {
            "name": "asset_last_updated_timestamp",
            "description": "Last updated timestamp",
            "labels": ["symbol", "asset_type"],
            "key": "asset_last_updated",
        },
        # 10. 株式固有メトリクス（統合不可）
        {
            "name": "stock_pe_ratio",
            "description": "Price to Earnings ratio (stocks only)",
            "labels": ["symbol", "name", "exchange"],
            "key": "stock_pe_ratio",
        },
        # 11. 株式固有メトリクス（統合不可）
        {
            "name": "stock_dividend_yield",
            "description": "Dividend yield percentage (stocks only)",
            "labels": ["symbol", "name", "exchange"],
            "key": "stock_dividend_yield",
        },
    ],
    "counters": [
        # 12. 統合エラーカウンター（4個のエラーメトリクスを1個に統合）
        {
            "name": "asset_fetch_errors_total",
            "description": "Total asset fetch errors",
            "labels": ["symbol", "error_type", "asset_type"],
            "key": "asset_fetch_errors",
        },
    ],
    "histograms": [
        # 13. 統合フェッチ時間（4個の時間メトリクスを1個に統合）
        {
            "name": "asset_fetch_duration_seconds",
            "description": "Time spent fetching asset data",
            "labels": ["symbol", "asset_type"],
            "key": "asset_fetch_duration",
        },
    ],
}

# asset_type の値定義
ASSET_TYPES = {
    "STOCK": "stock",      # 株式
    "FOREX": "forex",      # 為替
    "INDEX": "index",      # 指数
    "CRYPTO": "crypto",    # 暗号通貨
}

# 統合効果
REDUCTION_IMPACT = {
    "before": 43,  # 統合前のメトリクス数
    "after": 13,   # 統合後のメトリクス数
    "reduction": 30,  # 削減数
    "reduction_percent": 69.8,  # 削減率（%）
}

# 利点
BENEFITS = [
    "スケーラビリティ向上: 新しい資産タイプ追加時のメトリクス爆発を防止",
    "クエリ簡素化: asset_type ラベルでフィルタリング可能",
    "保守性向上: 単一メトリクスの管理で済む",
    "Prometheusベストプラクティス準拠: ラベルベースの分類",
    "メモリ使用量削減: メトリクス定義数の大幅削減",
]

# 注意点
CONSIDERATIONS = [
    "既存のダッシュボードやアラートの更新が必要",
    "一部のクエリでlabel filteringが必要になる",
    "asset_type=\"stock\" のようなフィルタリングが必要",
    "株式固有メトリクス（PE比、配当利回り）は統合不可",
]