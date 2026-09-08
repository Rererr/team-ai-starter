#!/usr/bin/env python3
"""このテンプレートが TeamAI のチームリポジトリとして通るかを、外部サービスなしで確かめる。

隔離した HOME と、自己署名証明書のローカル HTTPS git サーバーを立て、
`teamai init` → `teamai pull` → `teamai doctor` を実行して rules/docs の配布を確認する。
続けて Stop Hook を直接流し、共有の案内が `sharing.contributeHint.enabled` で止まること（0.23 以降）を確かめる。
前提: teamai (npm i -g teamai-cli), git, openssl。本人の ~/ と本物のチームリポジトリには触れない。
"""
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent


class GitHttp(BaseHTTPRequestHandler):
    """git http-backend を CGI として呼ぶ最小のサーバー。認証なし・テスト専用。"""
    root = ""

    def _run(self):
        u = urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        env = dict(os.environ, GIT_PROJECT_ROOT=self.root, GIT_HTTP_EXPORT_ALL="1",
                   REQUEST_METHOD=self.command, PATH_INFO=u.path, QUERY_STRING=u.query,
                   CONTENT_TYPE=self.headers.get("Content-Type", ""), CONTENT_LENGTH=str(length),
                   REMOTE_ADDR="127.0.0.1", GATEWAY_INTERFACE="CGI/1.1", SERVER_PROTOCOL="HTTP/1.1")
        if self.headers.get("Content-Encoding"):
            env["HTTP_CONTENT_ENCODING"] = self.headers["Content-Encoding"]
        out = subprocess.run(["git", "http-backend"], input=body, env=env, capture_output=True).stdout
        head, _, payload = out.partition(b"\r\n\r\n")
        status, headers = 200, []
        for line in head.decode().splitlines():
            key, _, value = line.partition(":")
            if key.lower() == "status":
                status = int(value.strip().split()[0])
            else:
                headers.append((key, value.strip()))
        self.send_response(status)
        for key, value in headers:
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = _run

    def log_message(self, *_):
        pass


def sh(*args, env, cwd=None, check=True):
    result = subprocess.run(args, env=env, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise SystemExit(f"失敗: {' '.join(map(str, args))}\n{result.stdout}\n{result.stderr}")
    return result


def share_hint_emitted(teamai, home, env, session, correction):
    """摩擦の高いセッションを装って Stop Hook を流し、共有の案内が出たかを返す。

    案内の条件は「tool_use が 15 件以上」かつ「摩擦の点数が 20 以上」。
    訂正は、直前の stop から 60 秒以内の prompt_submit が訂正キーワードを含むときに 1 件（20 点）と数えられる。
    """
    events = home / ".teamai/dashboard/events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    base = datetime.now(timezone.utc) - timedelta(minutes=2)

    def event(offset, **fields):
        stamp = (base + timedelta(seconds=offset)).isoformat().replace("+00:00", "Z")
        return json.dumps({"timestamp": stamp, "sessionId": session, "tool": "claude", "cwd": str(home), **fields})

    lines = [event(i, type="tool_use", toolName="Bash" if i % 2 else "Read") for i in range(16)]
    lines.append(event(20, type="stop"))
    lines.append(event(25, type="prompt_submit", promptSummary=correction))
    with events.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    transcript = home / f"{session}.jsonl"
    transcript.write_text("", encoding="utf-8")
    stdin = json.dumps({"session_id": session, "cwd": str(home), "transcript_path": str(transcript), "hook_event_name": "Stop"})
    # dispatcher は切り離した子プロセスを残すことがあるため、パイプでなくファイルへ出力させる
    out = home / f"{session}.stdout"
    with out.open("w", encoding="utf-8") as f:
        subprocess.run([teamai, "hook-dispatch", "stop", "--tool", "claude"], input=stdin, env=env, cwd=home,
                       stdout=f, stderr=subprocess.DEVNULL, text=True, timeout=60)
    return "share-learnings" in out.read_text(encoding="utf-8")


def main():
    teamai = shutil.which("teamai")
    if not teamai:
        raise SystemExit("teamai が PATH に無い（npm install -g teamai-cli）")
    version = subprocess.run([teamai, "--version"], capture_output=True, text=True).stdout.strip()
    major, minor = map(int, re.match(r"(\d+)\.(\d+)", version).groups())
    hint_setting_supported = (major, minor) >= (0, 23)  # sharing.contributeHint.enabled は 0.23.0-beta.8 から
    # 0.22 は日本語の訂正キーワードを持たない（0.23.0-beta.7 から）ため、案内が出ること自体の確認には英語を使う
    correction = "違う、やり直して" if hint_setting_supported else "that's wrong, redo it"
    with tempfile.TemporaryDirectory(prefix="team-ai-starter-e2e-") as temporary:
        base = Path(temporary)
        home, org = base / "home", base / "org"
        (home / ".claude").mkdir(parents=True)
        (home / ".codex").mkdir()
        org.mkdir()
        env = dict(os.environ, HOME=str(home), GIT_SSL_NO_VERIFY="1")
        sh("git", "config", "--global", "user.name", "tester", env=env)
        sh("git", "config", "--global", "user.email", "tester@example.com", env=env)
        # TeamAI は https か ssh の URL しか受け付けないため、自己署名証明書で HTTPS を立てる
        sh("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(base / "key.pem"),
           "-out", str(base / "cert.pem"), "-days", "1", "-subj", "/CN=127.0.0.1", env=env)
        remote = org / "team.git"
        sh("git", "init", "-q", "--bare", "-b", "main", str(remote), env=env)
        sh("git", "-C", str(remote), "config", "http.receivepack", "true", env=env)
        work = base / "work"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "scripts", ".teamai"))
        GitHttp.root = str(base)
        server = ThreadingHTTPServer(("127.0.0.1", 0), GitHttp)  # 空きポートを OS に選ばせる
        url = f"https://127.0.0.1:{server.server_address[1]}/org/team.git"
        yaml = work / "teamai.yaml"
        yaml.write_text("\n".join(
            f"repo: {url}" if line.startswith("repo:") else "provider: git" if line.startswith("provider:") else line
            for line in yaml.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
        sh("git", "init", "-q", "-b", "main", str(work), env=env)
        sh("git", "-C", str(work), "add", "-A", env=env)
        sh("git", "-C", str(work), "commit", "-qm", "template", env=env)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(base / "cert.pem"), str(base / "key.pem"))
        server.socket = context.wrap_socket(server.socket, server_side=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            sh("git", "-C", str(work), "push", "-q", url, "HEAD:main", env=env)
            init = sh(teamai, "init", url, "--scope", "user", "--agent", "claude,codex", "--force", "--role", "none",
                      env=env, cwd=home)
            pull = sh(teamai, "pull", env=env, cwd=home)
            doctor = sh(teamai, "doctor", env=env, cwd=home)

            def publish(message):
                # init がメンバー登録を main へ push しているため、先に取り込む
                sh("git", "-C", str(work), "commit", "-qam", message, env=env)
                sh("git", "-C", str(work), "pull", "-q", "--rebase", url, "main", env=env)
                sh("git", "-C", str(work), "push", "-q", url, "HEAD:main", env=env)
                sh(teamai, "pull", env=env, cwd=home)

            # テンプレート既定（contributeHint.enabled: false）で共有の案内が止まるか
            hint_with_setting_off = share_hint_emitted(teamai, home, env, "e2e-hint-off", correction)
            # 同じ摩擦で、設定を true にすると案内が出るか（案内の条件を満たしていることの対照）
            yaml.write_text(yaml.read_text(encoding="utf-8").replace(
                "  contributeHint:\n    enabled: false\n", "  contributeHint:\n    enabled: true\n"), encoding="utf-8")
            publish("enable contribute hint")
            hint_with_setting_on = share_hint_emitted(teamai, home, env, "e2e-hint-on", correction)
            # hooks.yaml のコメントにある選択肢（内蔵 Stop Hook の停止）が実際に効くことも確かめる
            hooks_yaml = work / "hooks/hooks.yaml"
            hooks_yaml.write_text(hooks_yaml.read_text(encoding="utf-8").replace(
                "  disabled: []\n", '  disabled: ["Hook dispatch stop"]\n'), encoding="utf-8")
            publish("disable stop hook")
            settings_after = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))
        finally:
            server.shutdown()
        checks = {
            "init が成功": "initialized successfully" in init.stdout,
            "teamai.yaml を既定値で上書きしていない": "Creating default config" not in init.stdout,
            "rules が Claude Code へ配布": (home / ".claude/rules/team-boundaries.md").is_file(),
            "rules が Codex へ配布": (home / ".codex/rules/team-boundaries.md").is_file(),
            "docs が配布": (home / ".teamai/docs/README.md").is_file(),
            "personal-* スキルを配布していない": not list((home / ".claude/skills").glob("personal-*")),
            "Claude Code に内蔵 Hook が登録": "hook-dispatch" in (home / ".claude/settings.json").read_text(),
            "doctor が全通過": "All checks passed" in doctor.stdout,
            ("日本語の訂正" if hint_setting_supported else "英語の訂正") + "で共有の案内が出る（contributeHint.enabled: true）": hint_with_setting_on,
            ("contributeHint.enabled: false で共有の案内が止まる" if hint_setting_supported
             else f"contributeHint 未対応の {version} では案内が出続ける"): hint_with_setting_off == (not hint_setting_supported),
            "builtin.disabled で内蔵 Stop Hook が外れる": "hook-dispatch stop" not in json.dumps(settings_after),
            "他の内蔵 Hook は残る": "hook-dispatch session-start" in json.dumps(settings_after),
        }
        for label, ok in checks.items():
            print(("OK  " if ok else "NG  ") + label)
        if not all(checks.values()):
            print(init.stdout, pull.stdout, doctor.stdout, sep="\n---\n")
            raise SystemExit(1)
        print(json.dumps({"members": [p.name for p in (remote / "refs/heads").iterdir()]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
