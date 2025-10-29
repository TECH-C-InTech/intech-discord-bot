# Python 3.11をベースイメージとして使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# uvをインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 依存関係ファイルをコピー
COPY pyproject.toml uv.lock ./

# 依存関係をインストール（uvを使用）
RUN uv sync --frozen --no-dev

# アプリケーションコードをコピー
COPY . .

# Botを実行
CMD ["uv", "run", "bot.py"]
