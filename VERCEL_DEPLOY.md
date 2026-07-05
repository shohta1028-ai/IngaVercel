# Vercelへのデプロイ手順

このリポジトリ(`IngaVercel`)はVercelデプロイ専用です。フロントエンドと
バックエンドを**別々のVercelプロジェクト**としてデプロイします（1プロジェクト
にまとめる構成は、フロントエンドのビルド時に`VITE_API_BASE_URL`を正しく
空にし忘れるとローカルの`localhost:8000`を呼びに行ってしまう等、事故りやすい
ため、より単純なこの構成に変更しました）。

## 構成

同じGitHubリポジトリから、Vercelプロジェクトを**2つ**作成します。

| プロジェクト | Root Directory | 内容 |
|---|---|---|
| 例: `inga-analytics-frontend` | `frontend` | Vite/React |
| 例: `inga-analytics-backend` | `backend` | FastAPI(`app.api.main:app`) |

`backend/pyproject.toml`の`[tool.vercel] entrypoint = "app.api.main:app"`で
FastAPIの`app`インスタンスの場所をVercelに伝えている
（[FastAPI on Vercelの仕様](https://vercel.com/docs/frameworks/backend/fastapi)
に準拠）。`backend/vercel.json`でFunctionの`maxDuration`を60秒に設定している
（EDINET検索が日付範囲によっては時間がかかるため）。

フロントエンドとバックエンドは別ドメインになるため、フロントエンドの
`VITE_API_BASE_URL`にバックエンドの実際のデプロイURLを設定する。CORSは
backend側で`allow_origins=["*"]`済み（[backend/app/api/main.py](backend/app/api/main.py)）
のため追加対応は不要。

## 事前準備

- Vercelアカウント
- [EDINET](https://disclosure2.edinet-fsa.go.jp/)の無料APIキー（IRデータ
  取込みでEDINET検索機能を使う場合）
- Anthropic APIキー

## 手順

### 1. バックエンドを先にデプロイする

1. Vercelダッシュボードで「Add New」→「Project」
2. `IngaVercel`リポジトリをインポート
3. **Root Directory** を `backend` に設定する（重要）
4. Environment Variablesに以下を設定:

   | Key | Value |
   |---|---|
   | `ANTHROPIC_API_KEY` | (Anthropicのキー) |
   | `ANTHROPIC_MODEL` | 例: `claude-sonnet-5`（任意） |
   | `EDINET_API_KEY` | (EDINETのキー、任意) |

5. Deployを実行し、完了したらデプロイURLを控える
   （例: `https://inga-analytics-backend.vercel.app`）
6. 動作確認: `https://<バックエンドURL>/api/dag`にブラウザでアクセスし、
   DAGのJSONが返ってくることを確認する

### 2. フロントエンドをデプロイする

1. 同じ`IngaVercel`リポジトリからもう一つ「Add New」→「Project」
2. **Root Directory** を `frontend` に設定する（重要）
3. Environment Variablesに以下を設定:

   | Key | Value |
   |---|---|
   | `VITE_API_BASE_URL` | 手順1で控えたバックエンドのURL（末尾に`/`を付けない、例: `https://inga-analytics-backend.vercel.app`） |

4. Deployを実行する

### 3. 動作確認

- フロントエンドのURLを開き、初期DAG（シードデータ）が表示されること
- ブラウザの開発者ツール→Networkタブで、`/api/dag`等のリクエストが
  `localhost:8000`ではなく手順1のバックエンドURLに飛んでいることを確認
- 「IRデータ取込み」→「EDINETから検索」が動くこと（`EDINET_API_KEY`設定時）
- 「対話チューニング」「因果効果を推論する」等、LLM呼び出しを伴う機能が
  タイムアウトしないこと

## 既知の制約

- **DAG状態は永続化されません。** サーバーレス関数はリクエスト間・
  インスタンス間でファイルシステムの変更を保持しないため、`/tmp`に
  保存したDAG編集内容はコールドスタートや別インスタンスへの
  ルーティングで失われることがあります（プロトタイプとして許容する
  前提）。永続化が必要になった場合はVercel KV/Blob等の外部ストレージへの
  切り替えが別途必要
- `dowhy`・`pandas`・`numpy`・`statsmodels`等、backendの依存関係は
  比較的重量級です。Vercel Functionsのバンドルサイズ上限(500MB)には
  収まる見込みですが、コールドスタートが数秒かかることがあります
- `functions`の`maxDuration`は60秒に設定していますが、実際の上限は
  Vercelのプラン（Hobby/Pro等）によって異なります。EDINET検索がタイム
  アウトする場合は、検索期間を短くするか、プランのFunction実行時間上限を
  確認してください
- フロントエンドとバックエンドが別デプロイのため、バックエンドのURLが
  変わった場合（プロジェクトの再作成等）は、フロントエンド側の
  `VITE_API_BASE_URL`を更新して再デプロイする必要がある
