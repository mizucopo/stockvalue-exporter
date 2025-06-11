from flask import Flask, jsonify
import tomllib
from pathlib import Path

app = Flask(__name__)

def get_version():
    """pyproject.tomlからバージョンを取得"""
    try:
        # 現在のファイルと同じディレクトリのpyproject.tomlを読み込み
        pyproject_path = Path(__file__).parent / "pyproject.toml"

        if not pyproject_path.exists():
            return 1

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("version", "unknown")
    except Exception as e:
        print(f"Error reading version from pyproject.toml: {e}")
        return 1

def get_app_info():
    """アプリケーション情報を取得"""
    try:
        pyproject_path = Path(__file__).parent / "pyproject.toml"

        if not pyproject_path.exists():
            return {"name": "stockvalue-exporter", "version": "unknown", "description": "Unknown"}

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            project = data.get("project", {})
            return {
                "name": project.get("name", "stockvalue-exporter"),
                "version": project.get("version", "unknown"),
                "description": project.get("description", "Stock value exporter for Prometheus")
            }
    except Exception as e:
        print(f"Error reading app info from pyproject.toml: {e}")
        return {"name": "stockvalue-exporter", "version": "unknown", "description": "Unknown"}

# アプリケーション起動時に情報を取得
APP_INFO = get_app_info()
APP_NAME = APP_INFO["name"]
APP_VERSION = APP_INFO["version"]
APP_DESCRIPTION = APP_INFO["description"]

@app.route('/')
def health():
    """ヘルスチェック"""
    return f"{APP_NAME} v{APP_VERSION} is running!"

@app.route('/health')
def health_json():
    """ヘルスチェック（JSON形式）"""
    return jsonify({
        "name": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "status": "running",
        "message": f"{APP_NAME} v{APP_VERSION} is running!"
    })

@app.route('/version')
def version():
    """バージョン情報"""
    return jsonify({
        "name": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=False)
