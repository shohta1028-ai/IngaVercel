# テストの考え方（他プロジェクトへの持ち出し用）

IngaAnalyticsのbackendテストで実際に効いた判断基準をまとめたもの。
新規プロジェクトを始めるときは、このファイルをコピーして
プロジェクトのCLAUDE.mdやREADMEに転記するか、リンクして使う。

コードそのものは数行で書き直せるが、判断基準（なぜそうするか）を
忘れると同じ議論を繰り返すことになる。そのため各原則には
「なぜ」を必ず添えてある。

## 原則

### 1. 外部境界（非決定的・課金対象・ネットワーク依存）だけをモックする

それ以外（パース、マージ、計算ロジック）は本物のコードをそのまま実行する。

- 例（モックする）: LLM呼び出し（`backend/app/llm/template_generator.py`）
  — 呼ぶたびに課金され、出力は非決定的で、ネットワークに依存する。
- 例（モックしない）: 因果効果の推定（`backend/app/causal/effect_estimation.py`）
  — DoWhyによる決定的なローカル計算。モックする理由がない。

**なぜ**: モックを増やすほど「本物が動くこと」を検証できなくなる。
モックはコストがかかる・決定的でない境界にだけ使う、という線引きを
明確にしておかないと、便利だからという理由でどこにでもモックを
入れてしまい、テストがコードの動作を保証しなくなる。

### 2. モックの入れ方は依存性注入

対象の関数・クラスは `client: SomeClient | None = None` のような形で
外部クライアントを引数に取り、`None`なら本物を生成する
（`client = client or Anthropic()`）。テストは最小限のインターフェース
（例: `.messages.create()`）だけ満たすフェイッククラスを注入する。

```python
class _ScriptedAnthropicClient:
    """systemプロンプトの内容に応じて異なる固定JSONを返すフェイクLLMクライアント"""
    def __init__(self, responses_by_marker: dict[str, dict]):
        self._responses_by_marker = responses_by_marker
        self.messages = self

    def create(self, system: str, **kwargs):
        for marker, payload in self._responses_by_marker.items():
            if marker in system:
                return _FakeResponse(content=[_FakeTextBlock(text=json.dumps(payload))])
        raise AssertionError("未定義のsystemプロンプトが呼ばれました")
```
（実例: `backend/tests/test_dialogue.py`。雛形は`backend/tests/support/fake_llm_client.py`）

**なぜ**: モック用のライブラリ（`unittest.mock.patch`等）でグローバルに
差し替える方式は、差し替え漏れや副作用の把握が難しくなりがち。
関数のシグネチャで注入できるようにしておけば、本番コードにテスト用の
if分岐を一切増やさずに、テストごとに違う応答を用意できる。

### 3. 決定的な計算は「既知の正解」を用意して実計算で検証する

モックでは「呼ばれたか」しか検証できない。決定的なアルゴリズム
（回帰、集計、レイアウト計算等）は、正解が分かっている入力を用意し、
出力が理論値の許容範囲に収まることをアサートする。

例（`backend/app/causal/sample_data.py` + `backend/tests/test_effect_estimation.py`）:
係数が既知の合成データ（例: `cogs = 900 - 4*plant_utilization_rate + noise`）を
生成し、推定された効果が理論値（-4 × 別の係数）の近傍に収まることを検証する。

**なぜ**: 「動いているように見える」と「正しい答えが出ている」は別。
特に統計・数値計算コードは、実行時エラーが出ないことと結果が正しいことの
間に大きな溝がある。

### 4. APIレイヤーのテストは実フレームワークのTestClient + 状態の隔離

ファイルやDBに永続化するアプリは、`pytest`の`monkeypatch`でテスト時の
保存先を`tmp_path`に差し替え、本物の状態ファイルを汚さないようにする。

```python
@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(store_module, "CURRENT_DAG_PATH", tmp_path / "current_dag.json")
    from app.api.main import app
    return TestClient(app)
```
（実例: `backend/tests/test_api.py`）

**なぜ**: 実際のASGIアプリ（FastAPI等）に対してHTTPリクエストを送って
検証することで、ルーティング・バリデーション・エラーハンドリングまで
含めて検証できる。状態を隔離しないと、テストの実行順序によって
結果が変わったり、開発中の実データを壊したりする。

## ライブラリのbaseline

新規プロジェクトのrequirements.txtにそのままコピーできる最小セット。
このリポジトリ固有の依存（dowhy, networkx, pandas等）は含めない。

```
pytest>=8.0.0
fastapi>=0.115.0          # APIを作る場合のみ
httpx>=0.27.0             # fastapi.testclientの内部依存。明示しておくと安全
python-dotenv>=1.0.0      # .envベースでAPIキー等を管理する場合
```

`monkeypatch`・`tmp_path`はpytest本体に組み込み済みなので追加インストール不要。

### フロントエンドE2E

このリポジトリでは`playwright`を単体でスクリプト実行し、都度使い捨てで
動作確認していた（`node scripts/xxx.js`形式）。探索的な確認には手早いが、
リポジトリに残らず継続的に再実行もされない。

新規プロジェクトで最初から展開するなら、テストランナー込みの
`@playwright/test`を使い、`tests/*.spec.ts`として書いて
`npx playwright test`で継続的に回せる形にする方が展開の名に値する。

```
@playwright/test>=1.45.0
```

## 展開の仕方

- **プラクティス（この文書の中身）**: 新規プロジェクトのCLAUDE.mdに
  この文書へのリンクを貼るか、関連する原則だけ転記する。
- **雛形コード**: `backend/tests/support/fake_llm_client.py`をコピーし、
  対象の外部クライアントの形状（`.messages.create()`等）に合わせて
  数行書き換えて使う。抽象化しすぎたパッケージにはしない
  （プロジェクトごとに外部クライアントの形が違うため、コピー&微修正の
  ほうが結局使いやすい）。
