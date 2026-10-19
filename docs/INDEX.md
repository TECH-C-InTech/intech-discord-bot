# ドキュメント一覧

InTech Discord Botのドキュメントへのインデックスです。

## 📖 ドキュメント

### 基本ドキュメント

#### [README.md](../README.md)

プロジェクト概要とクイックスタートガイド

- プロジェクトの概要
- 機能一覧
- 簡単なセットアップ手順
- コマンド一覧

#### [CLAUDE.md](../CLAUDE.md)

Claude Code用のガイダンス（AI開発アシスタント向け）

- 開発コマンドのクイックリファレンス
- ドキュメント構造の概要
- 重要なアーキテクチャパターン
- 各種タスクのワークフロー

### セットアップ

#### [SETUP.md](./SETUP.md)

詳細なセットアップ手順とトラブルシューティング

- 環境構築の詳細手順
- Discord Botの設定方法
- 環境変数の説明
- よくあるエラーと解決方法

### 開発ガイド

#### [ARCHITECTURE.md](./ARCHITECTURE.md)

アーキテクチャと設計パターン

- 技術スタック
- デュアルサーバーアーキテクチャ
- 自動コマンド登録システム
- 設定管理（シングルトンパターン）
- 番号の採番とロールの並び
- 作成の直列化と上限チェック
- 記録の出し先（チャンネル内の記録・本人への返信）

#### [ADD_COMMAND.md](./ADD_COMMAND.md)

新しいコマンドの追加方法

- コマンドの追加手順
- デコレーター順序（重要）
- コマンドメタデータの使い方
- テンプレートの使い方

#### [UTILITIES.md](./UTILITIES.md)

ユーティリティ関数とヘルパー

- バリデーションユーティリティ
- メッセージユーティリティ
- チャンネルユーティリティ
- 作成と上限チェック
- 記録
- コマンドメタデータ
- ロギングパターン

#### [CLUB_CHANNEL.md](./CLUB_CHANNEL.md)

クラブチャンネル管理システムの仕様と実装

- クラブチャンネル作成機能の概要
- チャンネルとロールの一括管理
- メンバー管理とロール付与
- イベントチャンネルとの比較
- 実装例とベストプラクティス

#### [DEVELOPMENT.md](./DEVELOPMENT.md)

開発ワークフローとCI/CD

- 開発環境のセットアップ
- ブランチ戦略とコミット規則
- コードスタイルとリント
- CI/CDパイプライン
- デプロイ手順

## 🔧 使い方

### 初めての方

1. [README.md](../README.md) でプロジェクトを把握
2. [SETUP.md](./SETUP.md) でセットアップ
3. [ARCHITECTURE.md](./ARCHITECTURE.md) でアーキテクチャを理解

### 開発者

1. [DEVELOPMENT.md](./DEVELOPMENT.md) で開発環境を構築
2. [ADD_COMMAND.md](./ADD_COMMAND.md) で新機能追加
3. [UTILITIES.md](./UTILITIES.md) でユーティリティを活用
4. [CLUB_CHANNEL.md](./CLUB_CHANNEL.md) でクラブチャンネル管理を理解

### 困った時

- [SETUP.md](./SETUP.md) のトラブルシューティングを確認
- [ARCHITECTURE.md](./ARCHITECTURE.md) で設計パターンを確認
- [UTILITIES.md](./UTILITIES.md) でヘルパー関数の使い方を確認
- [CLUB_CHANNEL.md](./CLUB_CHANNEL.md) でクラブチャンネルの使い方を確認

## 📚 ドキュメント間の関連

```text
README.md (概要)
    ↓
SETUP.md (環境構築)
    ↓
ARCHITECTURE.md (アーキテクチャ理解)
    ↓
DEVELOPMENT.md (開発環境)
    ↓
ADD_COMMAND.md (コマンド追加) ← UTILITIES.md (ヘルパー関数)
    ↓
CLUB_CHANNEL.md (クラブチャンネル管理) ← (クラブ関連機能)
```
