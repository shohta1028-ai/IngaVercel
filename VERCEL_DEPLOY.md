# Vercelへのデプロイ手順

このファイルと`vercel.json`は`deploy/vercel`ブランチ専用です。`main`には
反映しません（Vercel用の設定・挙動変更をmainのコードから切り離すため）。

## 構成

Vercelの[Services](https://vercel.com/docs/services)機能を使い、1つの
Vercelプロジェクト内で以下2つのserviceを動かします。

- `frontend`: `frontend/`配下のVite/Reactアプリ
- `backend`: `backend/`配下のFastAPIアプリ（`app.api.main:app`）

`/api/*`へのリクエストは`backend`serviceに、それ以外は`frontend`service
にルーティングされます（`vercel.json`の`rewrites`）。同一オリジンで動く
ため、フロントエンドからのAPI呼び出しはCORSを気にせず相対パス
（例: `/api/dag`）で届きます。

## 事前準備

- Vercelアカウント、および対象GitHubリポジトリへのアクセス権
- [EDINET](https://disclosure2.edinet-fsa.go.jp/)の無料APIキー（IRデータ
  取込みでEDINET検索機能を使う場合）
- Anthropic APIキー

## 手順

1. Vercelダッシュボードで「New Project」からこのリポジトリをインポートする
2. デプロイ対象ブランチとして`deploy/vercel`を指定する
   （Production Branchをこのブランチにするか、Preview Deploymentとして
   このブランチを使う）
3. プロジェクトの Settings → Environment Variables に以下を設定する:

   | Key | Value | 備考 |
   |---|---|---|
   | `ANTHROPIC_API_KEY` | (Anthropicのキー) | 必須。テンプレート生成・対話チューニング・IR抽出で使用 |
   | `ANTHROPIC_MODEL` | 例: `claude-sonnet-5` | 任意。未設定時はコード側の既定値を使用 |
   | `EDINET_API_KEY` | (EDINETのキー) | EDINET検索機能を使う場合のみ |
   | `VITE_API_BASE_URL` | (空文字のまま) | **値を入力せず空にする**。フロントエンドが相対パス(`/api/...`)でbackend serviceを呼べるようにするため |

4. 「Deploy」を実行する
5. デプロイ完了後、以下を実機で確認する:
   - トップ画面が表示され、初期DAG（シードデータ）が見えること
   - 「IRデータ取込み」→「EDINETから検索」が動くこと
     （`EDINET_API_KEY`を設定した場合）
   - 「対話チューニング」「因果効果を推論する」等、LLM呼び出しを伴う機能が
     タイムアウトしないこと（特にEDINET検索は日付範囲が広いと時間が
     かかるため、まず短い期間で試す）

## 既知の制約

- **DAG状態は永続化されません。** サーバーレス関数はリクエスト間・
  インスタンス間でファイルシステムの変更を保持しないため、`/tmp`に
  保存したDAG編集内容はコールドスタートや別インスタンスへの
  ルーティングで失われることがあります（今回はこれを許容する前提で
  プロトタイプとしてデプロイしています）。永続化が必要になった場合は
  Vercel KV/Blob等の外部ストレージへの切り替えが別途必要です
- `dowhy`・`pandas`・`numpy`・`statsmodels`等、backendの依存関係は
  比較的重量級です。Vercel Functionsのバンドルサイズ上限(500MB)には
  収まる見込みですが、コールドスタートが数秒かかることがあります
- `functions`の`maxDuration`は60秒に設定していますが、実際の上限は
  Vercelのプラン（Hobby/Pro等）によって異なります。EDINET検索がタイム
  アウトする場合は、検索期間を短くするか、プランのFunction実行時間上限を
  確認してください
