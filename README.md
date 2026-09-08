# team-ai-starter

[TeamAI](https://github.com/Tencent/teamai-cli) で配布する、チームのルールと知識の最小テンプレートです。
個人の改善は [personal-ai-loop](https://github.com/Rererr/personal-ai-loop) が担い、このリポジトリはチームで採用した資産だけを持ちます。
会社やプロジェクト固有の情報は含めていません。

## 構成

| パス | 役割 | 配布のされ方 |
|---|---|---|
| `teamai.yaml` | チーム名、リポジトリ、共有ポリシー | TeamAI が読む |
| `rules/` | チーム規約（`team-boundaries.md` は個人とチームの境界） | `teamai pull` で各ツールの `rules/` へ |
| `docs/` | レビューで採用した知識と索引 | `teamai pull` で `~/.teamai/docs/` へ |
| `hooks/hooks.yaml` | チーム配布 Hook と内蔵 Hook の上書き | `teamai pull` で各ツールの設定へ |
| `scripts/e2e-local.py` | テンプレートが TeamAI で通ることをローカルだけで確かめる | 配布しない |

使わないスキル、エージェント、MCP、Hook の空の雛形は置いていません。必要になったときにディレクトリを足します。

## 管理者の手順

1. Git ホスト（GitHub、GitLab、GitCode、CNB、TGit、自前の Git）に private リポジトリを作り、メンバーへ書き込み権限を与える
2. このテンプレートの内容を置き、`teamai.yaml` の `team`、`repo`、`provider` を実際の値にする
3. デフォルトブランチにレビュー必須の保護を設定する（規約だけでは直接 push を止められない）
4. `hooks/hooks.yaml` で内蔵 Stop Hook を止めるかを決める（[共存の判断](docs/coexistence.md)）

配布前にローカルで検証できます。外部サービスに触れず、隔離した HOME と自己署名の HTTPS git サーバーで `teamai init` から `doctor` までを流します。
teamai のほかに Python 3、Git、openssl が要ります。

```bash
npm install -g teamai-cli
python3 scripts/e2e-local.py
```

## 新メンバーの手順

1. 個人用の `personal-ai-loop` を clone し、`python3 install.py` で使う AI ツールへ導入する
2. このテンプレートから作ったチームリポジトリを、担当プロジェクトへ接続する

```bash
npm install -g teamai-cli
cd /path/to/project
teamai init https://github.com/YOUR-ORG/YOUR-TEAM-REPO
```

セッション開始のたびに `teamai pull` が走り、rules と docs が各ツールへ同期されます。
Codex は追加された Hook を `/hooks` で信頼するまで実行しません。

## 担当範囲

| 個人側（personal-ai-loop） | チーム側（このリポジトリ） |
|---|---|
| 個人の好み、補助の受け方（`personal.md`） | 成果物と開発手順の規約（`rules/`） |
| 改善候補の検出と振り返り | 採用する共通知識のレビュー（`docs/`） |
| 個人のメモリ、会話ログ、個人用 knowledge リポジトリ | 一般化した設計判断と手順 |
| `personal-*` スキル | 必要になったチーム専用スキル |

## 知識を追加する

個人側の振り返りで共有候補が出たら、同じトピックが既にないか確認し、既存ファイルを更新するか新規ノートを作ります。
ノートには結論、適用条件、検証方法を含め、`docs/README.md` にリンクを追加します。
通常のブランチと PR でレビューし、採用後は `teamai pull` で配布されます。
個人のキュー、会話ログ、プロファイル、端末の絶対パスは持ち込みません。

skills、rules、agents は `teamai push` で MR を開けます。
docs、hooks、mcp は `teamai push` の対象外で、通常の commit と PR で更新します。

## TeamAI と併用するときに知っておくこと

- `teamai.yaml` の初期設定は自動 recall なし、チーム配布 Hook・MCP の自動反映なし、シェル設定への環境変数注入なしです。これらは TeamAI 内蔵の共有案内や利用統計の収集を止める設定ではありません
- TeamAI はセッション開始ごとに利用統計（スキル利用回数、割り込み・拒否・失敗の回数、トークン量）をこのリポジトリへ push します。会話本文は送りません。止める設定は 0.22.0 に無いため、展開前にメンバーへ説明してください
- TeamAI の共有案内（friction ヒント）と personal-ai-loop の振り返り案内は同じセッションで並び得ます。日本語の訂正は TeamAI 側の点数に入らないため、日本語のチームではほぼ重なりません。詳細と選択肢は [docs/coexistence.md](docs/coexistence.md) にあります

確認した版: TeamAI 0.22.0（`0ec7b77b`、2026-09-08）。ライセンスは MIT です。
参照: [TeamAI 公式](https://github.com/Tencent/teamai-cli)、[設定ガイド](https://github.com/Tencent/teamai-cli/blob/main/docs/usage-guide.md)。
