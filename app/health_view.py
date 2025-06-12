"""ヘルスチェックビューモジュール."""

from flask import Response, jsonify

from base_view import BaseView


class HealthView(BaseView):
    """ヘルスチェック用ビュークラス."""

    def get(self) -> Response:
        """アプリケーションのヘルスステータスを返す.

        Returns:
            アプリケーションの稼働状況情報を含むJSONレスポンス
        """
        return jsonify(
            {
                "name": self.app.name,
                "version": self.app.version,
                "description": self.app.description,
                "status": "running",
                "message": f"{self.app.name} v{self.app.version} is running!",
            }
        )
