from __future__ import annotations

import argparse
import html
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = ROOT / "projects"
RUN_DIR = ROOT / ".run"
LOG_DIR = ROOT / "logs"
CADDY_CONFIG = RUN_DIR / "caddy.json"
CONFIG_NAME = ".preview-router.toml"

DEFAULTS = {
    "tailscale_host": "newport.hedgehog-python.ts.net",
    "host_router_port": 18088,
    "ui_port": 18089,
    "caddy_container": "preview-caddy",
}


@dataclass
class Project:
    key: str
    path: Path
    name: str
    hostnames: list[str]
    app_host: str
    app_port: int
    caddy_port: int | None
    tailscale_port: int | None
    command: str
    setup: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    readiness_path: str = "/"
    readiness_statuses: list[int] = field(default_factory=lambda: [200, 302, 307, 308])

    @property
    def log_file(self) -> Path:
        return LOG_DIR / f"{self.key}.log"

    @property
    def pid_file(self) -> Path:
        return RUN_DIR / f"{self.key}.pid"

    @property
    def local_url(self) -> str:
        return f"http://127.0.0.1:{self.app_port}{self.readiness_path}"


def sh(cmd: list[str] | str, *, cwd: Path | None = None, check: bool = True, capture: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("$", cmd if isinstance(cmd, str) else " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), check=check, text=True, capture_output=capture, env=env)


def run_quiet(cmd: list[str]) -> None:
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def ensure_dirs() -> None:
    PROJECTS_DIR.mkdir(exist_ok=True)
    RUN_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)


def load_project(path: Path) -> Project:
    cfg_path = path / CONFIG_NAME
    if not cfg_path.exists():
        raise FileNotFoundError(f"Missing {cfg_path}")
    data = tomllib.loads(cfg_path.read_text())
    key = path.name
    return Project(
        key=key,
        path=path.resolve(),
        name=data.get("name", key),
        hostnames=list(data.get("hostnames", [f"{key}.newport"])),
        app_host=data.get("app_host", f"{key}.localhost"),
        app_port=int(data["app_port"]),
        caddy_port=int(data["caddy_port"]) if data.get("caddy_port") else None,
        tailscale_port=int(data["tailscale_port"]) if data.get("tailscale_port") else None,
        command=data["command"],
        setup=list(data.get("setup", [])),
        env={str(k): str(v) for k, v in dict(data.get("env", {})).items()},
        readiness_path=data.get("readiness_path", "/"),
        readiness_statuses=[int(x) for x in data.get("readiness_statuses", [200, 302, 307, 308])],
    )


def load_projects() -> list[Project]:
    ensure_dirs()
    projects = []
    for path in sorted(PROJECTS_DIR.iterdir()):
        if path.is_dir() or path.is_symlink():
            cfg = path / CONFIG_NAME
            if cfg.exists():
                projects.append(load_project(path))
    if not projects:
        raise SystemExit(f"No projects configured. Add symlinks under {PROJECTS_DIR} with {CONFIG_NAME} inside each target repo.")
    return projects


def is_port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.25)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_http(name: str, url: str, statuses: list[int], timeout: int = 120) -> None:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "preview-router/0.1"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status in statuses:
                    print(f"==> {name} ready at {url} ({resp.status})")
                    return
                last = f"HTTP {resp.status}"
        except urllib.error.HTTPError as e:
            if e.code in statuses:
                print(f"==> {name} ready at {url} ({e.code})")
                return
            last = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        time.sleep(1)
    raise SystemExit(f"ERROR: {name} did not become ready at {url}; last={last}")


def read_pid(pid_file: Path) -> int | None:
    try:
        return int(pid_file.read_text().strip())
    except Exception:
        return None


def stop_pid(pid_file: Path, name: str) -> None:
    pid = read_pid(pid_file)
    if not pid:
        return
    try:
        os.killpg(pid, signal.SIGTERM)
        print(f"==> stopped {name} process group {pid}")
        time.sleep(0.5)
        try:
            os.killpg(pid, 0)
            os.killpg(pid, signal.SIGKILL)
            print(f"==> killed lingering {name} process group {pid}")
        except ProcessLookupError:
            pass
    except ProcessLookupError:
        pass
    except PermissionError as e:
        print(f"WARN: could not stop {name} pid {pid}: {e}")
    pid_file.unlink(missing_ok=True)


def start_process(name: str, cmd: str | list[str], cwd: Path, log_file: Path, pid_file: Path, env_extra: dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    env.update(env_extra or {})
    log_file.parent.mkdir(exist_ok=True)
    log = log_file.open("ab")
    proc = subprocess.Popen(cmd, cwd=cwd, shell=isinstance(cmd, str), stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    pid_file.write_text(str(proc.pid))
    print(f"==> started {name} pid {proc.pid}; log {log_file}")


def stop_legacy_processes() -> None:
    patterns = [
        "portless proxy start",
        "portless dwellsmart",
        "portless siliconharbour",
        "portless where-the-plow",
        "mise run dev:web",
        "tsx watch server.ts",
        "uvicorn where_the_plow.main:app",
        "react-router dev",
        "workerd serve",
    ]
    for pat in patterns:
        subprocess.run(["pkill", "-f", pat], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def render_caddy(projects: list[Project]) -> dict[str, Any]:
    host_routes: list[dict[str, Any]] = [
        {
            "match": [{"host": ["preview.newport"]}],
            "handle": [{"handler": "reverse_proxy", "upstreams": [{"dial": f"127.0.0.1:{DEFAULTS['ui_port']}"}]}],
        }
    ]
    servers: dict[str, Any] = {
        "hostnames": {
            "listen": [f"127.0.0.1:{DEFAULTS['host_router_port']}"],
            "automatic_https": {"disable": True},
            "routes": host_routes,
        }
    }
    for p in projects:
        host_routes.append({
            "match": [{"host": p.hostnames}],
            "handle": [{
                "handler": "reverse_proxy",
                "upstreams": [{"dial": f"127.0.0.1:{p.app_port}"}],
                "headers": {"request": {"set": {"Host": [p.app_host]}}},
            }],
        })
        if p.caddy_port:
            servers[f"{p.key}_tailscale"] = {
                "listen": [f"127.0.0.1:{p.caddy_port}"],
                "routes": [{"handle": [{
                    "handler": "reverse_proxy",
                    "upstreams": [{"dial": f"127.0.0.1:{p.app_port}"}],
                    "headers": {"request": {"set": {"Host": [p.app_host]}}},
                }]}],
            }
    return {"admin": {"listen": "127.0.0.1:2019"}, "apps": {"http": {"servers": servers}}}


def start_caddy(projects: list[Project]) -> None:
    CADDY_CONFIG.write_text(json.dumps(render_caddy(projects), indent=2))
    run_quiet(["docker", "rm", "-f", str(DEFAULTS["caddy_container"])])
    sh([
        "docker", "run", "-d", "--rm", "--name", str(DEFAULTS["caddy_container"]), "--network", "host",
        "-v", f"{CADDY_CONFIG}:/etc/caddy/caddy.json:ro",
        "caddy:2-alpine", "caddy", "run", "--config", "/etc/caddy/caddy.json",
    ])


def start_tailscale(projects: list[Project]) -> None:
    for p in projects:
        if p.tailscale_port and p.caddy_port:
            run_quiet(["tailscale", "serve", "--https", str(p.tailscale_port), "off"])
            sh(["tailscale", "serve", "--bg", f"--https={p.tailscale_port}", f"http://127.0.0.1:{p.caddy_port}"])


def stop_tailscale(projects: list[Project]) -> None:
    for p in projects:
        if p.tailscale_port:
            run_quiet(["tailscale", "serve", "--https", str(p.tailscale_port), "off"])


def cmd_start(args: argparse.Namespace) -> None:
    ensure_dirs()
    projects = load_projects()
    if args.clean:
        cmd_stop(argparse.Namespace(legacy=True))
    else:
        stop_legacy_processes()
    start_process("preview UI", ["uv", "run", "preview-router", "ui", "--port", str(DEFAULTS["ui_port"])], ROOT, LOG_DIR / "ui.log", RUN_DIR / "ui.pid")
    wait_http("preview UI", f"http://127.0.0.1:{DEFAULTS['ui_port']}/health", [200], 30)

    for p in projects:
        for setup in p.setup:
            sh(setup, cwd=p.path)
        env = {"HOST": "127.0.0.1", "PORT": str(p.app_port)}
        env.update(p.env)
        start_process(p.name, p.command, p.path, p.log_file, p.pid_file, env)
    for p in projects:
        wait_http(p.name, p.local_url, p.readiness_statuses, 120)

    start_caddy(projects)
    wait_http("Caddy preview UI route", f"http://127.0.0.1:{DEFAULTS['host_router_port']}/health", [200], 30)
    for p in projects:
        if p.caddy_port:
            wait_http(f"Caddy {p.name} route", f"http://127.0.0.1:{p.caddy_port}{p.readiness_path}", p.readiness_statuses, 30)

    start_tailscale(projects)

    print("\nPreview ready:")
    print(f"  UI:              http://preview.newport/  or http://preview.newport:{DEFAULTS['host_router_port']}/")
    for p in projects:
        primary = f"http://{p.hostnames[0]}/"
        local = f"http://{p.hostnames[0]}:{DEFAULTS['host_router_port']}/"
        ts = f"https://{DEFAULTS['tailscale_host']}:{p.tailscale_port}/" if p.tailscale_port else ""
        print(f"  {p.name:<16} {primary:<34} {local:<42} {ts}")


def cmd_stop(args: argparse.Namespace) -> None:
    ensure_dirs()
    projects = []
    try:
        projects = load_projects()
    except SystemExit:
        pass
    for p in projects:
        stop_pid(p.pid_file, p.name)
    stop_pid(RUN_DIR / "portless-proxy.pid", "portless proxy")
    stop_pid(RUN_DIR / "ui.pid", "preview UI")
    stop_tailscale(projects)
    run_quiet(["docker", "rm", "-f", str(DEFAULTS["caddy_container"])])
    if getattr(args, "legacy", False):
        stop_legacy_processes()


def probe(url: str, statuses: list[int] | None = None) -> str:
    statuses = statuses or [200, 302, 307, 308]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "preview-router/0.1"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return f"{resp.status} ok" if resp.status in statuses else f"{resp.status} unexpected"
    except urllib.error.HTTPError as e:
        return f"{e.code} ok" if e.code in statuses else f"{e.code} error"
    except Exception as e:  # noqa: BLE001
        return f"down: {type(e).__name__}"


def collect_status() -> dict[str, Any]:
    projects = load_projects()
    return {
        "ports": {"host_router": is_port_open(int(DEFAULTS["host_router_port"])), "ui": is_port_open(int(DEFAULTS["ui_port"]))},
        "projects": [
            {
                "key": p.key,
                "name": p.name,
                "hosts": p.hostnames,
                "pid": read_pid(p.pid_file),
                "local": probe(p.local_url, p.readiness_statuses),
                "host_url": f"http://{p.hostnames[0]}/",
                "port_url": f"http://{p.hostnames[0]}:{DEFAULTS['host_router_port']}/",
                "tailscale_url": f"https://{DEFAULTS['tailscale_host']}:{p.tailscale_port}/" if p.tailscale_port else None,
            }
            for p in projects
        ],
    }


def cmd_status(args: argparse.Namespace) -> None:
    print(json.dumps(collect_status(), indent=2))


class UIHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        try:
            status = collect_status()
            body = render_ui(status).encode()
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:  # noqa: BLE001
            body = html.escape(str(e)).encode()
            self.send_response(500)
            self.send_header("content-type", "text/plain")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def render_ui(status: dict[str, Any]) -> str:
    rows = []
    for p in status["projects"]:
        links = [f'<a href="{html.escape(p["host_url"])}">{html.escape(p["host_url"])}</a>', f'<a href="{html.escape(p["port_url"])}">:18088</a>']
        if p.get("tailscale_url"):
            links.append(f'<a href="{html.escape(p["tailscale_url"])}">Tailscale HTTPS</a>')
        rows.append(f"<tr><td>{html.escape(p['name'])}</td><td>{html.escape(', '.join(p['hosts']))}</td><td>{html.escape(str(p['local']))}</td><td>{' · '.join(links)}</td></tr>")
    ports = " · ".join(f"{k}: {'up' if v else 'down'}" for k, v in status["ports"].items())
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Newport previews</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem;background:#0b1020;color:#eef}}a{{color:#8bd3ff}}table{{border-collapse:collapse;width:100%;background:#121a33}}td,th{{padding:.75rem;border-bottom:1px solid #2b365f;text-align:left}}code{{background:#1c2645;padding:.15rem .35rem;border-radius:.25rem}}.muted{{color:#aab}}</style>
</head><body><h1>Newport previews</h1><p class='muted'>{html.escape(ports)}</p><table><thead><tr><th>Project</th><th>Hosts</th><th>Local status</th><th>Links</th></tr></thead><tbody>{''.join(rows)}</tbody></table><p>Control: <code>uv run preview-router start</code> · <code>uv run preview-router stop</code> · <code>uv run preview-router status</code></p></body></html>"""


def cmd_ui(args: argparse.Namespace) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", args.port), UIHandler)
    print(f"UI listening on http://127.0.0.1:{args.port}")
    server.serve_forever()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="preview-router")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_start = sub.add_parser("start")
    p_start.add_argument("--clean", action="store_true", default=True, help="stop old preview processes first (default)")
    p_start.set_defaults(func=cmd_start)
    p_stop = sub.add_parser("stop")
    p_stop.add_argument("--legacy", action="store_true", help="also pkill old shell-script preview processes")
    p_stop.set_defaults(func=cmd_stop)
    p_status = sub.add_parser("status")
    p_status.set_defaults(func=cmd_status)
    p_ui = sub.add_parser("ui")
    p_ui.add_argument("--port", type=int, default=int(DEFAULTS["ui_port"]))
    p_ui.set_defaults(func=cmd_ui)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
