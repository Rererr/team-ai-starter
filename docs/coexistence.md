# personal-ai-loop との共存

このリポジトリはチームの共有資産だけを持ち、個人の改善は [personal-ai-loop](https://github.com/Rererr/personal-ai-loop) に任せます。
両方を入れた環境で何が起き、何を選べるかをまとめます。
確認した TeamAI は 0.22.0（`0ec7b77b`）、0.23.0-beta.8、0.24.0 で、CI は 3 版で `scripts/e2e-local.py` を実行しています。

## 通知が重なる条件

TeamAI の Stop Hook は、割り込み・ツール実行の拒否・訂正・ツール失敗を点数化し、ツール呼び出し 15 回以上のセッションで閾値を超えると共有を促します。
訂正キーワードは 0.22.0 までは中国語と英語だけで、日本語の訂正は点数に入りませんでした。
0.23.0-beta.7 から日本語の訂正表現（「違う」「やり直し」「勝手に」など）も数えられます（[Tencent/teamai-cli#431](https://github.com/Tencent/teamai-cli/pull/431)）。
personal-ai-loop は日本語と英語の修正・承認表現を検出してローカルのキューへ積みます。

0.23 以降では、日本語で作業するチームでも TeamAI 側の案内が出ます。
出た場合も `rules/team-boundaries.md` の規約どおり、共有の承認とは扱いません。

## 共有の案内だけを止める

このテンプレートの `teamai.yaml` は `sharing.contributeHint.enabled: false` を既定にしています（[Tencent/teamai-cli#432](https://github.com/Tencent/teamai-cli/pull/432)、0.23.0-beta.8 以降）。
共有の案内だけが止まり、内蔵 Stop Hook の他の役割（CLI の更新確認、recall 投票の同期、ダッシュボード報告）は動き続けます。
メンバー個人が上書きするには、ローカル設定の `contributeHintEnabled` か環境変数 `TEAMAI_CONTRIBUTE_HINT_DISABLED=1` を使います。
0.22 以前はこのキーを無視するため、案内は出続けます（`doctor` は通ります）。

## 内蔵 Stop Hook を止める選択

0.22 以前で案内を止めるには、`hooks/hooks.yaml` の `builtin.disabled` に `"Hook dispatch stop"` を加えます。次の `teamai pull` で全メンバーの Stop Hook が外れます。
この Hook が担う CLI の更新確認、recall 投票の同期、ダッシュボード報告も止まります。
更新確認は `teamai update`、投票同期は次の `teamai pull` で代替できます。

## 利用統計の送信

TeamAI はセッション開始の `teamai pull` ごとに、スキル利用回数、割り込み・拒否・失敗の回数、トークン量を `stats/<user>.yaml` と `votes/<user>.yaml` へ commit と push します。
会話本文は送りません。

このテンプレートの `teamai.yaml` は `usageReport: false` で送信を止めています（[Tencent/teamai-cli#505](https://github.com/Tencent/teamai-cli/pull/505)、0.24.0 以降）。
0.23 以前はこのキーを無視して push を続けるため、その版を使うなら展開前にメンバーへ説明してください。
どちらの挙動も `scripts/e2e-local.py` が利用イベントを仕込んで確かめます（0.24.0 では送られず、ローカルの `~/.teamai/usage.jsonl` に残る。0.23.0-beta.8 では送られる）。
0.25 系では送信先が既定ブランチから `teamai-reports` という orphan ブランチへ変わりますが、止める設定は同じです。

## 設定ディレクトリを移している Claude Code

Claude Code は `CLAUDE_CONFIG_DIR` で設定ディレクトリ全体（settings.json、hooks、skills、rules、`.claude.json`）を `~/.claude` 以外へ移せます。仕事用と個人用のアカウントを分けているメンバーが使います。
0.24.0 時点の TeamAI は Claude Code のパスを `~/.claude` 固定で解決し、この変数を参照しません。
そのため `CLAUDE_CONFIG_DIR=~/.claude-work` のメンバーでは、`teamai init` と `teamai pull` が `~/.claude` へ書き、その Claude Code は何も読みません。SessionStart の `teamai pull` は走らず、`teamai doctor` は緑のままです。

0.26.0 以降は、`teamai init` が `CLAUDE_CONFIG_DIR` を本人単位の設定 `toolRoots.claude` に記録し、`doctor` が不一致を警告します（[Tencent/teamai-cli#725](https://github.com/Tencent/teamai-cli/issues/725)、[#728](https://github.com/Tencent/teamai-cli/pull/728)。2026-09-24 マージ、v0.26.0-beta.2 以降に収録）。
0.25 以前を使う場合は、該当メンバーに `teamai pull` を手動で回してもらうか、そのメンバーだけ 0.26.0 以降へ上げてください。

## learnings の直接 push

`teamai contribute` は `learnings/` へレビューなしで既定ブランチへ push します。
この運用では skills / rules / agents は `teamai push`（MR）、docs は通常の PR で提案し、`contribute` は使いません。
`learnings/` を使う場合はチームで合意し、その旨を README に書いてください。
