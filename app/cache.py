"""効率的なキャッシュシステムモジュール."""

import time
from collections import OrderedDict
from collections.abc import Iterator
from typing import Any, Generic, TypeVar

from config import config

T = TypeVar("T")


class LRUCache(Generic[T]):
    """メモリ制限とTTL機能を持つLRUキャッシュクラス."""

    def __init__(
        self, max_size: int | None = None, ttl_seconds: int | None = None
    ) -> None:
        """LRUキャッシュを初期化する.

        Args:
            max_size: キャッシュの最大サイズ（Noneの場合は設定から取得）
            ttl_seconds: キャッシュのTTL秒数（Noneの場合は設定から取得）
        """
        self.max_size = max_size or config.CACHE_MAX_SIZE
        self.ttl_seconds = ttl_seconds or config.CACHE_TTL_SECONDS
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def get(self, key: str) -> T | None:
        """キャッシュから値を取得する.

        Args:
            key: キャッシュキー

        Returns:
            キャッシュされた値。見つからないかTTL切れの場合はNone
        """
        if key not in self._cache:
            return None

        # TTLチェック
        if self._is_expired(key):
            self._remove(key)
            return None

        # LRU: 最近使用されたものとして移動
        self._cache.move_to_end(key)

        value: T = self._cache[key]["value"]
        return value

    def put(self, key: str, value: T) -> None:
        """キャッシュに値を設定する.

        Args:
            key: キャッシュキー
            value: キャッシュする値
        """
        current_time = time.time()

        if key in self._cache:
            # 既存の項目を更新
            self._cache[key] = {"value": value, "created_at": current_time}
            self._cache.move_to_end(key)
        else:
            # 新しい項目を追加
            if len(self._cache) >= self.max_size:
                self._evict_lru()

            self._cache[key] = {"value": value, "created_at": current_time}

    def clear(self) -> None:
        """キャッシュをクリアする."""
        self._cache.clear()

    def size(self) -> int:
        """現在のキャッシュサイズを取得する.

        Returns:
            キャッシュ内のアイテム数
        """
        return len(self._cache)

    def _is_expired(self, key: str) -> bool:
        """キーが期限切れかチェックする.

        Args:
            key: チェックするキー

        Returns:
            期限切れの場合True
        """
        if key not in self._cache:
            return True

        created_at = float(self._cache[key]["created_at"])
        return time.time() - created_at > self.ttl_seconds

    def _remove(self, key: str) -> None:
        """キーをキャッシュから削除する.

        Args:
            key: 削除するキー
        """
        if key in self._cache:
            del self._cache[key]

    def _evict_lru(self) -> None:
        """LRU（最も使用されていない）アイテムを削除する."""
        if not self._cache:
            return

        # OrderedDictの最初の項目（最も古い）を削除
        oldest_key = next(iter(self._cache))
        self._remove(oldest_key)

    def cleanup_expired(self) -> int:
        """期限切れのアイテムをクリーンアップする.

        Returns:
            削除されたアイテム数
        """
        expired_keys = [key for key in self._cache.keys() if self._is_expired(key)]

        for key in expired_keys:
            self._remove(key)

        return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """キャッシュの統計情報を取得する.

        Returns:
            統計情報の辞書。memory_usage_ratioは有効（期限切れでない）アイテムの比率を示す
        """
        expired_count = sum(1 for key in self._cache.keys() if self._is_expired(key))
        active_items = len(self._cache) - expired_count

        # max_size が 0 の場合の ZeroDivisionError を防ぐ
        memory_usage_ratio = active_items / self.max_size if self.max_size > 0 else 0.0
        storage_usage_ratio = (
            len(self._cache) / self.max_size if self.max_size > 0 else 0.0
        )

        return {
            "total_items": len(self._cache),
            "active_items": active_items,
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "expired_items": expired_count,
            "memory_usage_ratio": memory_usage_ratio,
            "storage_usage_ratio": storage_usage_ratio,
        }

    # Dict-like interface for backward compatibility
    def __getitem__(self, key: str) -> T:
        """Dict-like item access."""
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: str, value: T) -> None:
        """Dict-like item assignment."""
        self.put(key, value)

    def __delitem__(self, key: str) -> None:
        """Dict-like item deletion."""
        if key not in self._cache:
            raise KeyError(key)
        self._remove(key)

    def __contains__(self, key: str) -> bool:
        """Dict-like membership test."""
        return key in self._cache and not self._is_expired(key)

    def __len__(self) -> int:
        """Dict-like length.

        Returns:
            Number of non-expired items in cache

        Note:
            This method returns only non-expired items for consistency
            with other dict-like operations like __contains__.
        """
        return len([key for key in self._cache if not self._is_expired(key)])

    def __iter__(self) -> Iterator[str]:
        """Dict-like iteration over keys.

        Returns:
            Iterator over non-expired keys only

        Note:
            This method returns only non-expired keys for consistency
            with other dict-like operations like __contains__ and __len__.
        """
        return iter(key for key in self._cache.keys() if not self._is_expired(key))

    def keys(self) -> Iterator[str]:
        """Dict-like keys method.

        Returns:
            Iterator over non-expired keys only

        Note:
            This method returns only non-expired keys for consistency
            with other dict-like operations like __contains__ and __len__.
        """
        return iter(key for key in self._cache.keys() if not self._is_expired(key))

    def __eq__(self, other: object) -> bool:
        """Dict-like equality comparison.

        Note:
            Only compares non-expired items for consistency
            with other dict-like operations.
        """
        if isinstance(other, dict):
            # Get non-expired items only
            non_expired_keys = [
                k for k in self._cache.keys() if not self._is_expired(k)
            ]
            if len(other) == 0 and len(non_expired_keys) == 0:
                return True
            # For non-empty dicts, convert to dict and compare (non-expired items only)
            cache_dict = {k: self._cache[k]["value"] for k in non_expired_keys}
            return cache_dict == other
        return False
