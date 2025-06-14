"""LRUCacheクラスのテストモジュール."""

import time
from unittest.mock import patch

import pytest

from cache import LRUCache


class TestLRUCache:
    """LRUCacheクラスのテストケース."""

    def test_basic_operations(self) -> None:
        """基本的なget/put操作をテストする."""
        cache: LRUCache[str] = LRUCache(max_size=3, ttl_seconds=60)

        # 基本的なput/get
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

        # 存在しないキー
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self) -> None:
        """LRU削除をテストする."""
        cache: LRUCache[str] = LRUCache(max_size=2, ttl_seconds=60)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")  # key1が削除される

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_ttl_expiration(self) -> None:
        """TTL期限切れをテストする."""
        cache: LRUCache[str] = LRUCache(max_size=10, ttl_seconds=1)

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

        # TTL切れをシミュレート
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_dict_like_interface_with_expired_items(self) -> None:
        """期限切れアイテムを含むdict-likeインターフェースをテストする."""
        cache: LRUCache[str] = LRUCache(max_size=10, ttl_seconds=60)

        # アイテムを追加
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # 通常の状態をテスト
        assert len(cache) == 3
        assert "key1" in cache
        assert "key2" in cache
        assert "key3" in cache
        assert list(cache.keys()) == ["key1", "key2", "key3"]
        assert list(cache) == ["key1", "key2", "key3"]

    def test_dict_like_interface_with_expired_items_filtered(self) -> None:
        """期限切れアイテムがフィルタリングされることをテストする."""
        cache: LRUCache[str] = LRUCache(max_size=10, ttl_seconds=1)

        # アイテムを追加
        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # 一部のキーを期限切れにする
        with patch.object(cache, "_is_expired") as mock_is_expired:
            # key1は期限切れ、key2は有効
            mock_is_expired.side_effect = lambda k: k == "key1"

            # __len__は期限切れを除外
            assert len(cache) == 1

            # __contains__は期限切れを除外
            assert "key1" not in cache
            assert "key2" in cache

            # keys()は期限切れを除外
            assert list(cache.keys()) == ["key2"]

            # __iter__は期限切れを除外
            assert list(cache) == ["key2"]

    def test_dict_like_getitem_setitem_delitem(self) -> None:
        """dict-like __getitem__, __setitem__, __delitem__をテストする."""
        cache: LRUCache[str] = LRUCache(max_size=10, ttl_seconds=60)

        # __setitem__
        cache["key1"] = "value1"
        assert cache.get("key1") == "value1"

        # __getitem__
        assert cache["key1"] == "value1"

        # 存在しないキーでKeyError
        with pytest.raises(KeyError):
            _ = cache["nonexistent"]

        # __delitem__
        del cache["key1"]
        assert cache.get("key1") is None

        # 存在しないキーの削除でKeyError
        with pytest.raises(KeyError):
            del cache["nonexistent"]

    def test_dict_like_equality(self) -> None:
        """dict-like等価比較をテストする."""
        cache: LRUCache[str] = LRUCache(max_size=10, ttl_seconds=60)

        # 空のキャッシュ
        assert cache == {}

        # アイテムを追加
        cache["key1"] = "value1"
        cache["key2"] = "value2"

        expected_dict = {"key1": "value1", "key2": "value2"}
        assert cache == expected_dict

        # 期限切れアイテムは比較から除外される
        with patch.object(cache, "_is_expired") as mock_is_expired:
            mock_is_expired.side_effect = lambda k: k == "key1"

            expected_dict_filtered = {"key2": "value2"}
            assert cache == expected_dict_filtered

    def test_cleanup_expired(self) -> None:
        """期限切れアイテムのクリーンアップをテストする."""
        cache: LRUCache[str] = LRUCache(max_size=10, ttl_seconds=1)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # TTL切れをシミュレート
        time.sleep(1.1)

        # クリーンアップ前は内部ストレージにアイテムが残っている
        assert len(cache._cache) == 3

        # クリーンアップ実行
        removed_count = cache.cleanup_expired()
        assert removed_count == 3
        assert len(cache._cache) == 0

    def test_get_stats_with_expired_items(self) -> None:
        """期限切れアイテムを含む統計情報をテストする."""
        cache: LRUCache[str] = LRUCache(max_size=10, ttl_seconds=60)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        with patch.object(cache, "_is_expired") as mock_is_expired:
            mock_is_expired.side_effect = lambda k: k == "key1"

            stats = cache.get_stats()
            assert stats["total_items"] == 2  # 内部ストレージの実際のアイテム数
            assert stats["expired_items"] == 1  # 期限切れアイテム数
            assert stats["max_size"] == 10
            assert stats["ttl_seconds"] == 60

    def test_update_existing_item(self) -> None:
        """既存アイテムの更新をテストする."""
        cache: LRUCache[str] = LRUCache(max_size=10, ttl_seconds=60)

        cache.put("key1", "value1")
        cache.put("key1", "updated_value")

        assert cache.get("key1") == "updated_value"
        assert len(cache) == 1

    def test_clear_operation(self) -> None:
        """クリア操作をテストする."""
        cache: LRUCache[str] = LRUCache(max_size=10, ttl_seconds=60)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        assert len(cache) == 2

        cache.clear()

        assert len(cache) == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_size_method_vs_len(self) -> None:
        """size()メソッドと__len__の違いをテストする."""
        cache: LRUCache[str] = LRUCache(max_size=10, ttl_seconds=60)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        with patch.object(cache, "_is_expired") as mock_is_expired:
            mock_is_expired.side_effect = lambda k: k == "key1"

            # size()は内部ストレージのサイズ（期限切れ含む）
            assert cache.size() == 2

            # len()は期限切れを除外
            assert len(cache) == 1

    def test_consistency_across_dict_operations(self) -> None:
        """dict-like操作間の一貫性をテストする."""
        cache: LRUCache[str] = LRUCache(max_size=10, ttl_seconds=60)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        with patch.object(cache, "_is_expired") as mock_is_expired:
            # key1とkey3を期限切れにする
            mock_is_expired.side_effect = lambda k: k in ["key1", "key3"]

            # 全ての操作で同じ結果（期限切れ除外）が得られる
            valid_keys = ["key2"]

            assert len(cache) == len(valid_keys)
            assert list(cache.keys()) == valid_keys
            assert list(cache) == valid_keys
            assert all(key in cache for key in valid_keys)
            assert not any(key in cache for key in ["key1", "key3"])
