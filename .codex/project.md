# StockValue Exporter の作業指示

- 着手前に GitHub Issue を作成または確認し、その Issue に対応する非 `main` ブランチで作業する。
- ファイルの移動・削除には `git mv`・`git rm` を使う。
- 利用方法やインターフェースが変わる場合は README と関連文書を更新する。

## Copier 更新時に維持する固有の構成

- `src` は相対 import を使う既存のアプリケーション package。空の `src/__init__.py`、`python -m src.main` と Gunicorn の `src.main:web` を維持する。mypy の `explicit_package_bases` は指定せず、既存 package として検査する。
- 公開設定の `release_paths` は現行の標準 Docker Release では使われない。Python でも `version`・`revision` が生成宣言に残る問題は `mizucopo/repo-template#157` で追跡する。
- `pyproject.toml` の製品依存、pytest-cov と 80% の coverage gate、テストマーカーを維持する。バージョンは公開 workflow が採番し、更新 PR では変更しない。
- Dockerfile の非 root ユーザー、キャッシュの書き込み先、9100 番ポートを維持する。`.dockerignore` では Dockerfile が COPY する manifest・README・Python source と開発用 Dockerfile だけを許可する。
- PR の標準品質 gate に加えて、container runtime の UID/GID・書き込み権限・`/health` を確認する。
- Docker 公開対象は `linux/amd64` と `linux/arm64`。既存の Dependabot による Actions pin を保持し、Git tag は `.github/release.json` の `v{version}` を使う。
- Docker Hub secret は `DOCKERHUB_TOKEN` を優先し、旧 `DOCKER_TOKEN` の互換入力を維持する。
