# personal-ai-loop との共存

このリポジトリはチームの共有資産だけを持ち、個人の改善は [personal-ai-loop](https://github.com/YOUR-NAME/personal-ai-loop) に任せます。
両方を入れた環境で何が起き、何を選べるかをまとめます。
確認した TeamAI は 0.22.0（`0ec7b77b`）です。

## 通知が重なる条件

TeamAI の Stop Hook は、割り込み・ツール実行の拒否・訂正・ツール失敗を点数化し、ツール呼び出し 15 回以上のセッションで閾値を超えると共有を促します。
訂正キーワードは中国語と英語だけで、日本語の訂正は点数に入りません。
personal-ai-loop は日本語と英語の修正・承認表現を検出してローカルのキューへ積みます。

日本語で作業するチームでは、TeamAI 側の案内はほぼ出ません。
出た場合も `rules/team-boundaries.md` の規約どおり、共有の承認とは扱いません。

## 内蔵 Stop Hook を止める選択

`hooks/hooks.yaml` の `builtin.disabled` に `"Hook dispatch stop"` を加えると、次の `teamai pull` で全メンバーの Stop Hook が外れます。
共有の案内だけを止める設定は 0.22.0 に無く、この Hook が担う CLI の更新確認、recall 投票の同期、ダッシュボード報告も止まります。案内だけを止める設定は上流へ提案中です（[Tencent/teamai-cli#432](https://github.com/Tencent/teamai-cli/pull/432)）。マージ後は `sharing.contributeHint.enabled: false` で代替できます。
更新確認は `teamai update`、投票同期は次の `teamai pull` で代替できます。

## 利用統計の送信

TeamAI はセッション開始の `teamai pull` ごとに、スキル利用回数、割り込み・拒否・失敗の回数、トークン量を `stats/<user>.yaml` と `votes/<user>.yaml` へ commit と push します。
会話本文は送りません。止める設定は 0.22.0 に無いため、展開前にメンバーへ説明してください。

## learnings の直接 push

`teamai contribute` は `learnings/` へレビューなしで既定ブランチへ push します。
この運用では skills / rules / agents は `teamai push`（MR）、docs は通常の PR で提案し、`contribute` は使いません。
`learnings/` を使う場合はチームで合意し、その旨を README に書いてください。
