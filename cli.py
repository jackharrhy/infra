#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "click",
#     "pyyaml",
#     "octodns>=1.0",
#     "octodns-digitalocean",
#     "octodns-ddns",
#     "synology-api>=0.8",
#     "pyotp>=2.9",
# ]
# ///
"""Infra CLI - tools for managing and visualizing infrastructure."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click
import yaml

REPO_ROOT = Path(__file__).parent
HOSTS_DIR = REPO_ROOT / "hosts"
INFRA_YML = REPO_ROOT / "infra.yml"
DOCS_DIR = REPO_ROOT / "docs"
DNS_DIR = REPO_ROOT / "dns"
DNS_CONFIG = DNS_DIR / "config.yaml"
DNS_ZONES_DIR = DNS_DIR / "zones"
DNS_SECRET = DNS_DIR / "secrets" / "digitalocean.enc.yaml"

NAS_DIR = REPO_ROOT / "nas"
NAS_SECRET = NAS_DIR / "secrets" / "synology.enc.yaml"
# Tracks the unix-timestamp window of the last TOTP code we burned, so
# back-to-back CLI invocations don't replay the same 6-digit code (DSM
# rejects replays within the window and returns a confusing privileges
# error). Lives outside the repo since it's transient state.
NAS_OTP_STATE = Path.home() / ".cache" / "infra" / "nas-otp-window"

INFRA_SERVICES = {"traefik", "watchtower", "beszel", "beszel-agent"}
DB_IMAGE_PREFIXES = ("postgres:", "mysql:", "mariadb:", "mongo:", "redis:")


# --- Data models ---


@dataclass
class Service:
    name: str
    image: str
    domains: list[str] = field(default_factory=list)
    path_rules: list[str] = field(default_factory=list)
    networks: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    category: str = "unknown"  # website, database, infra, bot


@dataclass
class Host:
    name: str
    services: list[Service] = field(default_factory=list)


# --- Compose parsing ---


def parse_traefik_labels(labels: list[str]) -> tuple[list[str], list[str]]:
    """Extract domains and path rules from Traefik labels."""
    domains: list[str] = []
    path_rules: list[str] = []

    for label in labels:
        if not isinstance(label, str):
            continue

        # Match Host(`...`) patterns
        host_matches = re.findall(r"Host\(`([^`]+)`\)", label)
        domains.extend(host_matches)

        # Match PathPrefix(`...`) patterns
        path_matches = re.findall(r"PathPrefix\(`([^`]+)`\)", label)
        path_rules.extend(path_matches)

    return domains, path_rules


def is_traefik_enabled(labels: list[str]) -> bool:
    """Check if traefik.enable=true is in labels."""
    return any(
        isinstance(l, str) and "traefik.enable=true" in l
        for l in labels
    )


def categorize_service(name: str, image: str, labels: list[str], networks: list[Any]) -> str:
    """Determine the category of a service."""
    if name in INFRA_SERVICES:
        return "infra"

    if any(image.startswith(prefix) for prefix in DB_IMAGE_PREFIXES):
        return "database"

    if is_traefik_enabled(labels):
        return "website"

    # On web network but no traefik labels yet (e.g. livebook, pad with TODO)
    network_names = _extract_network_names(networks)
    if "web" in network_names:
        return "website"

    return "bot"


def _extract_network_names(networks: Any) -> list[str]:
    """Extract network names from compose networks field (list or dict)."""
    if isinstance(networks, list):
        return networks
    if isinstance(networks, dict):
        return list(networks.keys())
    return []


def parse_compose(host_name: str, compose_path: Path) -> Host:
    """Parse a compose.yml file into a Host with categorized Services."""
    with open(compose_path) as f:
        data = yaml.safe_load(f)

    host = Host(name=host_name)
    services_data: dict[str, Any] = data.get("services", {})

    for svc_name, svc_config in services_data.items():
        if svc_config is None:
            continue

        image = svc_config.get("image", "")
        labels = svc_config.get("labels", [])
        networks = svc_config.get("networks", [])
        depends_on = svc_config.get("depends_on", [])

        if isinstance(depends_on, dict):
            depends_on = list(depends_on.keys())

        domains, path_rules = parse_traefik_labels(labels)
        # Deduplicate while preserving order
        domains = list(dict.fromkeys(domains))
        all_path_rules = list(dict.fromkeys(path_rules))
        # If there's a bare `/` catch-all, the specific paths are secondary routes
        has_catch_all = "/" in all_path_rules
        path_rules = [p for p in all_path_rules if p != "/"]
        if has_catch_all:
            path_rules = []  # domain-level service, paths are secondary
        category = categorize_service(svc_name, image, labels, networks)

        service = Service(
            name=svc_name,
            image=image,
            domains=domains,
            path_rules=path_rules,
            networks=_extract_network_names(networks),
            depends_on=depends_on if isinstance(depends_on, list) else [depends_on],
            category=category,
        )
        host.services.append(service)

    return host


def discover_hosts() -> list[Host]:
    """Discover and parse all host compose files."""
    hosts = []
    if not HOSTS_DIR.exists():
        click.echo(f"Warning: {HOSTS_DIR} does not exist", err=True)
        return hosts

    for host_dir in sorted(HOSTS_DIR.iterdir()):
        if not host_dir.is_dir():
            continue
        compose_path = host_dir / "compose.yml"
        if compose_path.exists():
            hosts.append(parse_compose(host_dir.name, compose_path))

    return hosts


# --- infra.yml parsing ---


def load_infra_config() -> dict[str, Any]:
    """Load the infra.yml config file."""
    if not INFRA_YML.exists():
        click.echo(f"Warning: {INFRA_YML} does not exist, skipping extra context", err=True)
        return {}
    with open(INFRA_YML) as f:
        return yaml.safe_load(f) or {}


# --- D2 generation ---


def _d2_id(name: str) -> str:
    """Convert a name to a valid D2 identifier."""
    # D2 allows most characters in identifiers, but we quote if needed
    if re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", name):
        return name
    return f'"{name}"'


def _service_display_name(svc: Service) -> str:
    """Get a human-readable display name for a service."""
    if svc.domains:
        primary = svc.domains[0]
        # Only append path if there's exactly one domain and one path rule
        # (indicates a path-based sub-route like jackharrhy.dev/bar).
        # Multiple domains or paths means the paths are secondary routes.
        if len(svc.domains) == 1 and len(svc.path_rules) == 1:
            return f"{primary}{svc.path_rules[0]}"
        return primary
    return svc.name


def _service_tooltip(svc: Service) -> str | None:
    """Get a tooltip showing all domains if there are multiple."""
    if len(svc.domains) > 1:
        return ", ".join(svc.domains)
    return None


def _host_label(name: str, specs: dict[str, Any] | None) -> str:
    """Generate a D2 label for a host, including specs if available."""
    if not specs:
        return name
    parts = []
    if "cores" in specs:
        parts.append(f"{specs['cores']} cores")
    if "ram" in specs:
        parts.append(str(specs["ram"]))
    if "storage" in specs:
        parts.append(f"{specs['storage']} disk")
    spec_line = " / ".join(parts)
    return f'"{name} ({spec_line})"'


def generate_d2(hosts: list[Host], config: dict[str, Any]) -> str:
    """Generate D2 diagram source from parsed hosts and config."""
    lines: list[str] = []
    lines.append("direction: down")
    lines.append("")

    providers = config.get("providers", {})
    network = config.get("network", {})
    extra_nodes = config.get("extra_nodes", {})
    connections = config.get("connections", [])
    host_specs = config.get("hosts", {})

    # Build provider -> host mapping
    provider_hosts: dict[str, list[str]] = {}
    for provider_id, provider_conf in providers.items():
        provider_hosts[provider_id] = provider_conf.get("hosts", [])

    # Track D2 path for each host (for database connections etc.)
    host_paths: dict[str, str] = {}
    for provider_id, provider_conf in providers.items():
        for host_name in provider_conf.get("hosts", []):
            host_paths[host_name] = f"{provider_id}.{host_name}"
    for node_id, node_conf in extra_nodes.items():
        for host_name in node_conf.get("hosts", []):
            host_paths[host_name] = f"{node_id}.{host_name}"

    # Render network nodes (e.g. Tailscale)
    for net_id, net_conf in network.items():
        label = net_conf.get("label", net_id)
        shape = net_conf.get("shape", "cloud")
        lines.append(f"{_d2_id(net_id)}: {label} {{")
        lines.append(f"  shape: {shape}")
        lines.append("}")
        lines.append("")

    # Render providers with hosts inside
    host_map = {h.name: h for h in hosts}

    for provider_id, provider_conf in providers.items():
        label = provider_conf.get("label", provider_id)
        lines.append(f"{_d2_id(provider_id)}: {label} {{")

        for host_name in provider_conf.get("hosts", []):
            host = host_map.get(host_name)
            label = _host_label(host_name, host_specs.get(host_name))
            if not host:
                lines.append(f"  {_d2_id(host_name)}: {label}")
                continue

            lines.append(f"  {_d2_id(host_name)}: {label} {{")
            _render_host_services(lines, host, indent=4)
            lines.append("  }")
            lines.append("")

        lines.append("}")
        lines.append("")

    # Render extra nodes
    for node_id, node_conf in extra_nodes.items():
        label = node_conf.get("label", node_id)
        children = node_conf.get("children", {})
        node_hosts = node_conf.get("hosts", [])
        shape = node_conf.get("shape")

        if children or node_hosts:
            lines.append(f"{_d2_id(node_id)}: {label} {{")

            # Render hosts inside this extra node
            for host_name in node_hosts:
                host = host_map.get(host_name)
                host_label = _host_label(host_name, host_specs.get(host_name))
                if not host:
                    lines.append(f"  {_d2_id(host_name)}: {host_label}")
                    continue

                lines.append(f"  {_d2_id(host_name)}: {host_label} {{")
                _render_host_services(lines, host, indent=4)
                lines.append("  }")
                lines.append("")

            for child_id, child_conf in children.items():
                child_label = child_conf.get("label", child_id)
                child_shape = child_conf.get("shape", "rectangle")
                lines.append(f"  {_d2_id(child_id)}: {child_label} {{")
                lines.append(f"    shape: {child_shape}")
                lines.append("  }")
            lines.append("}")
        else:
            lines.append(f"{_d2_id(node_id)}: {label} {{")
            if shape:
                lines.append(f"  shape: {shape}")
            lines.append("}")
        lines.append("")

    # Render network connections
    for net_id, net_conf in network.items():
        connects = net_conf.get("connects", [])
        for target in connects:
            # Convert dotted path to D2 path
            d2_target = ".".join(_d2_id(p) for p in target.split("."))
            lines.append(f"{_d2_id(net_id)} -- {d2_target}")
        lines.append("")

    # Render explicit connections (e.g. traefik proxy)
    for conn in connections:
        from_path = ".".join(_d2_id(p) for p in conn["from"].split("."))
        to_path = ".".join(_d2_id(p) for p in conn["to"].split("."))
        conn_label = conn.get("label", "")
        if conn_label:
            lines.append(f"{from_path} -> {to_path}: {conn_label}")
        else:
            lines.append(f"{from_path} -> {to_path}")
    if connections:
        lines.append("")

    # Render service-to-database connections
    for host_name, host_path in host_paths.items():
        host = host_map.get(host_name)
        if not host:
            continue
        _render_db_connections(lines, host, host_path)

    return "\n".join(lines).rstrip() + "\n"


def _render_host_services(lines: list[str], host: Host, indent: int = 4) -> None:
    """Render categorized services for a host into D2 lines."""
    pad = " " * indent

    websites = [s for s in host.services if s.category == "website"]
    databases = [s for s in host.services if s.category == "database"]
    infra = [s for s in host.services if s.category == "infra"]
    bots = [s for s in host.services if s.category == "bot"]

    if infra:
        lines.append(f"{pad}infra: Infrastructure {{")
        lines.append(f"{pad}  grid-columns: 1")
        for svc in infra:
            lines.append(f"{pad}  {_d2_id(svc.name)}: {svc.name}")
        lines.append(f"{pad}}}")
        lines.append("")

    if websites:
        lines.append(f"{pad}websites: Websites {{")
        lines.append(f"{pad}  grid-columns: 2")
        for svc in websites:
            display = _service_display_name(svc)
            tooltip = _service_tooltip(svc)
            lines.append(f"{pad}  {_d2_id(svc.name)}: {display}")
            if tooltip:
                lines.append(f"{pad}  {_d2_id(svc.name)}.tooltip: {tooltip}")
        lines.append(f"{pad}}}")
        lines.append("")

    if databases:
        lines.append(f"{pad}databases: Databases {{")
        lines.append(f"{pad}  grid-columns: 1")
        for svc in databases:
            # Show the postgres version in the label
            img_short = svc.image.split("/")[-1] if "/" in svc.image else svc.image
            lines.append(f"{pad}  {_d2_id(svc.name)}: {svc.name} ({img_short}) {{")
            lines.append(f"{pad}    shape: cylinder")
            lines.append(f"{pad}  }}")
        lines.append(f"{pad}}}")
        lines.append("")

    if bots:
        lines.append(f"{pad}bots: Bots & Workers {{")
        lines.append(f"{pad}  grid-columns: 2")
        for svc in bots:
            lines.append(f"{pad}  {_d2_id(svc.name)}: {svc.name}")
        lines.append(f"{pad}}}")
        lines.append("")


def _render_db_connections(lines: list[str], host: Host, host_path: str) -> None:
    """Render connections between services and their databases."""
    db_names = {s.name for s in host.services if s.category == "database"}
    svc_map = {s.name: s for s in host.services}

    for svc in host.services:
        if svc.category == "database":
            continue
        for dep in svc.depends_on:
            if dep in db_names:
                svc_cat = "websites" if svc.category == "website" else "bots"
                lines.append(
                    f"{host_path}.{svc_cat}.{_d2_id(svc.name)} "
                    f"-> {host_path}.databases.{_d2_id(dep)}"
                )

        # Also check shared networks (for db connections without depends_on)
        for other_name in db_names:
            other = svc_map[other_name]
            shared_nets = set(svc.networks) & set(other.networks)
            # Exclude the general 'web' network
            shared_nets -= {"web"}
            if shared_nets and other_name not in svc.depends_on:
                svc_cat = "websites" if svc.category == "website" else "bots"
                lines.append(
                    f"{host_path}.{svc_cat}.{_d2_id(svc.name)} "
                    f"-> {host_path}.databases.{_d2_id(other_name)}"
                )


# --- Remote host helpers ---


def get_deploy_hosts(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Get hosts that have SSH deploy info from infra.yml.

    Returns a dict of host_name -> {ssh, repo_path, compose_path}.
    """
    hosts_conf = config.get("hosts", {})
    deploy_hosts: dict[str, dict[str, str]] = {}
    for name, conf in hosts_conf.items():
        if not isinstance(conf, dict):
            continue
        ssh = conf.get("ssh")
        if ssh:
            deploy_hosts[name] = {
                "ssh": ssh,
                "repo_path": conf.get("repo_path", "~/infra"),
                "compose_path": conf.get("compose_path", f"~/infra/hosts/{name}"),
            }
    return deploy_hosts


def ssh_run(ssh_target: str, command: str, *, stream: bool = False) -> subprocess.CompletedProcess[str] | int:
    """Run a command on a remote host via SSH.

    If stream=True, streams output live and returns the exit code.
    Otherwise returns a CompletedProcess.
    """
    ssh_cmd = ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", ssh_target, command]
    if stream:
        result = subprocess.run(ssh_cmd)
        return result.returncode
    return subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)


def get_local_head() -> str:
    """Get the local HEAD commit hash."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return result.stdout.strip()


def get_local_commits() -> set[str]:
    """Get all local commit hashes (for ahead/behind detection)."""
    result = subprocess.run(
        ["git", "log", "--format=%H"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return set(result.stdout.strip().splitlines())


# --- CLI ---


@click.group()
def cli():
    """Infra CLI - tools for managing and visualizing infrastructure."""
    pass


@cli.command()
@click.option(
    "--output", "-o",
    default=str(DOCS_DIR / "infra.d2"),
    help="Output path for the .d2 file",
    show_default=True,
)
@click.option(
    "--render/--no-render",
    default=True,
    help="Render the .d2 file to SVG using the d2 CLI",
    show_default=True,
)
@click.option(
    "--format", "-f",
    "fmt",
    default="svg",
    type=click.Choice(["svg", "png", "pdf"]),
    help="Output format for rendering",
    show_default=True,
)
def diagram(output: str, render: bool, fmt: str):
    """Generate an infrastructure diagram from compose files."""
    click.echo("Discovering hosts...")
    hosts = discover_hosts()
    if not hosts:
        click.echo("No hosts found.", err=True)
        sys.exit(1)

    for host in hosts:
        svc_count = len(host.services)
        click.echo(f"  {host.name}: {svc_count} services")

    config = load_infra_config()

    click.echo("Generating D2 diagram...")
    d2_source = generate_d2(hosts, config)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(d2_source)
    click.echo(f"Written: {output_path}")

    if render:
        render_path = output_path.with_suffix(f".{fmt}")
        d2_bin = shutil.which("d2")
        if not d2_bin:
            click.echo(
                "Warning: d2 CLI not found. Install from https://github.com/terrastruct/d2",
                err=True,
            )
            click.echo(f"You can render manually: d2 {output_path} {render_path}", err=True)
            return

        click.echo(f"Rendering to {render_path}...")
        result = subprocess.run(
            [d2_bin, str(output_path), str(render_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            click.echo(f"d2 rendering failed:\n{result.stderr}", err=True)
            sys.exit(1)
        click.echo(f"Rendered: {render_path}")


@cli.command()
@click.argument("host", required=False)
def status(host: str | None):
    """Show sync status between local and remote hosts."""
    config = load_infra_config()
    deploy_hosts = get_deploy_hosts(config)

    if not deploy_hosts:
        click.echo("No deploy hosts configured in infra.yml", err=True)
        sys.exit(1)

    targets = deploy_hosts
    if host:
        if host not in deploy_hosts:
            click.echo(f"Unknown host: {host}. Available: {', '.join(deploy_hosts)}", err=True)
            sys.exit(1)
        targets = {host: deploy_hosts[host]}

    local_head = get_local_head()
    local_commits = get_local_commits()

    # Column widths
    name_w = max(len(n) for n in targets) + 2
    hash_w = 9  # 7-char short hash + padding

    click.echo(f"{'Host':<{name_w}} {'Local':<{hash_w}} {'Remote':<{hash_w}} Status")
    click.echo(f"{'─' * name_w} {'─' * hash_w} {'─' * hash_w} {'─' * 12}")

    for name, info in targets.items():
        remote_head = ""
        status_str = ""
        try:
            result = ssh_run(info["ssh"], f"git -C {info['repo_path']} rev-parse HEAD")
            if isinstance(result, int):
                status_str = click.style("error", fg="red")
            elif result.returncode != 0:
                status_str = click.style("error", fg="red")
            else:
                remote_head = result.stdout.strip()
                if remote_head == local_head:
                    status_str = click.style("synced", fg="green")
                elif remote_head in local_commits:
                    status_str = click.style("behind", fg="yellow")
                else:
                    status_str = click.style("ahead/diverged", fg="red")
        except (subprocess.TimeoutExpired, OSError):
            status_str = click.style("unreachable", fg="red")

        local_short = local_head[:7]
        remote_short = remote_head[:7] if remote_head else "???"
        click.echo(f"{name:<{name_w}} {local_short:<{hash_w}} {remote_short:<{hash_w}} {status_str}")


@cli.command()
@click.argument("host", required=False)
def update(host: str | None):
    """Pull latest commits on remote host(s)."""
    config = load_infra_config()
    deploy_hosts = get_deploy_hosts(config)

    if not deploy_hosts:
        click.echo("No deploy hosts configured in infra.yml", err=True)
        sys.exit(1)

    targets = deploy_hosts
    if host:
        if host not in deploy_hosts:
            click.echo(f"Unknown host: {host}. Available: {', '.join(deploy_hosts)}", err=True)
            sys.exit(1)
        targets = {host: deploy_hosts[host]}

    for name, info in targets.items():
        click.echo(f"── {name} ({info['ssh']}) ──")
        cmd = f"cd {info['repo_path']} && git pull"
        exit_code = ssh_run(info["ssh"], cmd, stream=True)
        if exit_code != 0:
            click.echo(click.style(f"  Failed (exit {exit_code})", fg="red"))
        click.echo()


@cli.command()
@click.argument("host", required=False)
def refresh(host: str | None):
    """Pull images, recreate containers, and prune on remote host(s)."""
    config = load_infra_config()
    deploy_hosts = get_deploy_hosts(config)

    if not deploy_hosts:
        click.echo("No deploy hosts configured in infra.yml", err=True)
        sys.exit(1)

    targets = deploy_hosts
    if host:
        if host not in deploy_hosts:
            click.echo(f"Unknown host: {host}. Available: {', '.join(deploy_hosts)}", err=True)
            sys.exit(1)
        targets = {host: deploy_hosts[host]}

    for name, info in targets.items():
        click.echo(f"── {name} ({info['ssh']}) ──")
        cmd = (
            f"cd {info['compose_path']}"
            f" && docker compose pull"
            f" && docker compose up -d"
            # label!=cmd.keep spares images that opt in to surviving the
            # prune (e.g. cmd's workspace image on newport, which is
            # unreferenced between agent runs by design). Harmless on
            # hosts with no labeled images.
            f' && docker image prune -a -f --filter "label!=cmd.keep"'
        )
        exit_code = ssh_run(info["ssh"], cmd, stream=True)
        if exit_code != 0:
            click.echo(click.style(f"  Failed (exit {exit_code})", fg="red"))
        click.echo()


@cli.command()
def install():
    """Install an `infra` shortcut to ~/.local/bin."""
    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    target = bin_dir / "infra"

    script = f"""#!/usr/bin/env bash
exec uv run --script {REPO_ROOT / "cli.py"} "$@"
"""
    target.write_text(script)
    target.chmod(0o755)
    click.echo(f"Installed: {target}")

    # Check if ~/.local/bin is on PATH
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    if str(bin_dir) not in path_dirs:
        click.echo(f"Note: {bin_dir} is not on your PATH. Add it with:")
        click.echo(f'  export PATH="{bin_dir}:$PATH"')


# --- DNS (octodns) helpers ---


def _decrypt_do_token() -> str:
    """Decrypt the DigitalOcean API token from SOPS."""
    if not DNS_SECRET.exists():
        click.echo(f"Error: {DNS_SECRET} not found", err=True)
        click.echo("Create it with: sops dns/secrets/digitalocean.enc.yaml", err=True)
        sys.exit(1)

    sops_bin = shutil.which("sops")
    if not sops_bin:
        click.echo("Error: sops CLI not found. Install from https://github.com/getsops/sops", err=True)
        sys.exit(1)

    result = subprocess.run(
        [sops_bin, "-d", "--output-type", "json", str(DNS_SECRET)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        click.echo(f"Error decrypting {DNS_SECRET}:\n{result.stderr}", err=True)
        sys.exit(1)

    data = json.loads(result.stdout)
    token = data.get("DIGITALOCEAN_TOKEN", "")
    if not token:
        click.echo(f"Error: DIGITALOCEAN_TOKEN not found in {DNS_SECRET}", err=True)
        sys.exit(1)

    return token


def _octodns_env() -> dict[str, str]:
    """Build environment with the decrypted DO token for octodns commands."""
    env = os.environ.copy()
    env["DIGITALOCEAN_TOKEN"] = _decrypt_do_token()
    return env


@cli.group()
def dns():
    """Manage DNS records with octodns."""
    pass


@dns.command()
@click.option("--zone", "-z", default="*", help="Zone to dump ('*' for all)", show_default=True)
@click.option("--lenient", is_flag=True, help="Ignore record validation errors")
def dump(zone: str, lenient: bool):
    """Pull DNS records from DigitalOcean into local zone files."""
    DNS_ZONES_DIR.mkdir(parents=True, exist_ok=True)
    env = _octodns_env()

    cmd = [
        sys.executable, "-m", "octodns.cmds.dump",
        "--config-file", str(DNS_CONFIG),
        "--output-dir", str(DNS_ZONES_DIR),
        zone, "digitalocean",
    ]
    if lenient:
        cmd.append("--lenient")

    click.echo(f"Dumping zone(s): {zone}")
    click.echo(f"  config: {DNS_CONFIG}")
    click.echo(f"  output: {DNS_ZONES_DIR}")
    click.echo()

    result = subprocess.run(cmd, env=env, cwd=REPO_ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)

    # List what was written
    zone_files = sorted(DNS_ZONES_DIR.glob("*.yaml"))
    zone_files = [f for f in zone_files if f.name != ".gitkeep"]
    if zone_files:
        click.echo()
        click.echo(f"Dumped {len(zone_files)} zone(s):")
        for zf in zone_files:
            click.echo(f"  {zf.name}")
    else:
        click.echo("No zone files written.", err=True)


@dns.command()
@click.argument("zones", nargs=-1)
@click.option("--debug", is_flag=True, help="Enable debug output")
def diff(zones: tuple[str, ...], debug: bool):
    """Show what DNS changes would be made (dry run)."""
    env = _octodns_env()

    cmd = [
        sys.executable, "-m", "octodns.cmds.sync",
        "--config-file", str(DNS_CONFIG),
    ]
    for z in zones:
        cmd.append(z)
    if debug:
        cmd.append("--debug")

    click.echo("Running octodns-sync (dry run)...")
    click.echo()
    result = subprocess.run(cmd, env=env, cwd=REPO_ROOT)
    sys.exit(result.returncode)


@dns.command()
@click.argument("zones", nargs=-1)
@click.option("--force", is_flag=True, help="Force through significant changes")
@click.option("--debug", is_flag=True, help="Enable debug output")
def sync(zones: tuple[str, ...], force: bool, debug: bool):
    """Push local DNS changes to DigitalOcean."""
    env = _octodns_env()

    # Always show the plan first
    cmd_plan = [
        sys.executable, "-m", "octodns.cmds.sync",
        "--config-file", str(DNS_CONFIG),
    ]
    for z in zones:
        cmd_plan.append(z)
    if debug:
        cmd_plan.append("--debug")

    click.echo("Planning changes (dry run)...")
    click.echo()
    result = subprocess.run(cmd_plan, env=env, cwd=REPO_ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)

    click.echo()
    if not click.confirm("Apply these changes?"):
        click.echo("Aborted.")
        sys.exit(0)

    cmd_apply = cmd_plan + ["--doit"]
    if force:
        cmd_apply.append("--force")

    click.echo()
    click.echo("Applying changes...")
    result = subprocess.run(cmd_apply, env=env, cwd=REPO_ROOT)
    sys.exit(result.returncode)


@dns.command("auto-sync")
@click.argument("zones", nargs=-1)
@click.option("--force", is_flag=True, help="Force through significant changes")
def auto_sync(zones: tuple[str, ...], force: bool):
    """Non-interactive sync for automation (systemd timer / cron).

    Applies directly without the interactive confirmation that `sync` uses.
    Primarily for the octodns-ddns dynamic `craft` record: run on a schedule
    from newport so the home WAN IP stays current. octoDNS only writes when
    the value actually changes, so repeated runs are cheap no-ops.
    """
    env = _octodns_env()

    cmd = [
        sys.executable, "-m", "octodns.cmds.sync",
        "--config-file", str(DNS_CONFIG),
        "--doit",
    ]
    for z in zones:
        cmd.append(z)
    if force:
        cmd.append("--force")

    result = subprocess.run(cmd, env=env, cwd=REPO_ROOT)
    sys.exit(result.returncode)


# --- NAS (Synology DSM) helpers ---


def _decrypt_synology_creds() -> dict[str, Any]:
    """Decrypt Synology DSM credentials from SOPS.

    Expected keys in the secret:
      SYNOLOGY_HOST         - hostname or IP (e.g. stash.hedgehog-python.ts.net)
      SYNOLOGY_PORT         - DSM HTTPS port (e.g. 5001) or HTTP (5000)
      SYNOLOGY_USERNAME     - DSM account
      SYNOLOGY_PASSWORD     - DSM account password
      SYNOLOGY_SECURE       - "true" for HTTPS (default), "false" for HTTP
      SYNOLOGY_OTP          - (optional) one-shot 2FA code
      SYNOLOGY_TOTP_SECRET  - (optional) TOTP shared secret (base32);
                              if present, a fresh code is generated each login
                              and SYNOLOGY_OTP is ignored.
    """
    if not NAS_SECRET.exists():
        click.echo(f"Error: {NAS_SECRET} not found", err=True)
        click.echo(f"Create it with: sops {NAS_SECRET.relative_to(REPO_ROOT)}", err=True)
        sys.exit(1)

    sops_bin = shutil.which("sops")
    if not sops_bin:
        click.echo("Error: sops CLI not found. Install from https://github.com/getsops/sops", err=True)
        sys.exit(1)

    result = subprocess.run(
        [sops_bin, "-d", "--output-type", "json", str(NAS_SECRET)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        click.echo(f"Error decrypting {NAS_SECRET}:\n{result.stderr}", err=True)
        sys.exit(1)

    data = json.loads(result.stdout)
    required = ("SYNOLOGY_HOST", "SYNOLOGY_USERNAME", "SYNOLOGY_PASSWORD")
    missing = [k for k in required if not data.get(k)]
    if missing:
        click.echo(f"Error: missing keys in {NAS_SECRET}: {', '.join(missing)}", err=True)
        sys.exit(1)

    return data


def _resolve_synology_otp(creds: dict[str, Any]) -> str | None:
    """Resolve the OTP to pass to the DSM login call.

    Preference order: a stored TOTP secret (generates a fresh code), then a
    literal one-shot code, otherwise no 2FA.

    When using a TOTP secret, ensures the generated code is from a 30-second
    window that hasn't already been used by a prior CLI invocation (DSM
    rejects replays within the same window). Sleeps until the next window if
    needed — at most ~30s, usually 0.
    """
    totp_secret = creds.get("SYNOLOGY_TOTP_SECRET")
    if not totp_secret:
        return creds.get("SYNOLOGY_OTP") or None

    import time
    import pyotp

    totp = pyotp.TOTP(totp_secret)
    window = lambda t: int(t) // 30

    last_used: int | None = None
    if NAS_OTP_STATE.exists():
        try:
            last_used = int(NAS_OTP_STATE.read_text().strip())
        except (ValueError, OSError):
            last_used = None

    now = time.time()
    if last_used is not None and window(now) <= last_used:
        # We already burned a code in this (or a later — clock drift) window.
        # Wait until the next window starts, plus a small buffer for clock skew.
        next_window_start = (last_used + 1) * 30
        sleep_for = max(0.0, next_window_start - now) + 0.5
        if sleep_for > 0:
            click.echo(
                f"(Waiting {sleep_for:.1f}s for a fresh TOTP window...)",
                err=True,
            )
            time.sleep(sleep_for)
        now = time.time()

    code = totp.now()
    try:
        NAS_OTP_STATE.parent.mkdir(parents=True, exist_ok=True)
        NAS_OTP_STATE.write_text(str(window(now)))
    except OSError:
        pass  # best-effort; if cache write fails, login still works once
    return code


def _synology_client(api_class: str):
    """Return an instantiated synology-api client.

    api_class is one of: 'core_share', 'filestation', 'core_sys_info'.
    Lazy-imported so the dep isn't required for unrelated commands.
    """
    creds = _decrypt_synology_creds()
    secure = str(creds.get("SYNOLOGY_SECURE", "true")).lower() != "false"
    port = str(creds.get("SYNOLOGY_PORT", "5001" if secure else "5000"))
    common = dict(
        ip_address=creds["SYNOLOGY_HOST"],
        port=port,
        username=creds["SYNOLOGY_USERNAME"],
        password=creds["SYNOLOGY_PASSWORD"],
        secure=secure,
        cert_verify=False,
        dsm_version=7,
        debug=bool(os.environ.get("INFRA_NAS_DEBUG")),
        otp_code=_resolve_synology_otp(creds),
    )

    if api_class == "core_share":
        from synology_api.core_share import Share
        return Share(**common)
    if api_class == "filestation":
        from synology_api.filestation import FileStation
        return FileStation(**common)
    if api_class == "core_sys_info":
        from synology_api.core_sys_info import SysInfo
        return SysInfo(**common)
    raise ValueError(f"Unknown api_class: {api_class}")


@cli.group()
def nas():
    """Talk to the Synology NAS over the DSM API."""
    pass


@nas.command("login-check")
def nas_login_check():
    """Verify NAS credentials and print basic system info."""
    click.echo("Authenticating...")
    try:
        sysinfo = _synology_client("core_sys_info")
    except Exception as e:
        code = getattr(e, "error_code", None)
        if code is not None:
            click.echo(click.style(f"Login failed (DSM error {code}): {e}", fg="red"), err=True)
        else:
            click.echo(click.style(f"Login failed: {e}", fg="red"), err=True)
        sys.exit(1)
    try:
        info = sysinfo.sys_status()
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)

    data = info.get("data", info) if isinstance(info, dict) else {}
    click.echo(click.style("ok", fg="green"))
    if data:
        # Print a small, friendly subset (DSM keys vary across versions).
        for k in ("hostname", "model", "serial", "ram_size", "dsm_version",
                  "uptime", "is_dsm_boot_completed", "temperature"):
            if k in data:
                click.echo(f"  {k}: {data[k]}")


@nas.command("shares")
def nas_shares():
    """List shared folders on the NAS."""
    share = _synology_client("core_share")
    try:
        result = share.list_folders()
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)

    folders = (result.get("data") or {}).get("shares", [])
    if not folders:
        click.echo("No shared folders found.")
        return

    name_w = max(len(f.get("name", "")) for f in folders) + 2
    click.echo(f"{'Name':<{name_w}} {'Volume':<12} Description")
    click.echo(f"{'─' * name_w} {'─' * 12} {'─' * 30}")
    for f in folders:
        name = f.get("name", "")
        vol = f.get("vol_path", "")
        desc = f.get("desc", "") or ""
        click.echo(f"{name:<{name_w}} {vol:<12} {desc}")


# --- NFS share privilege helpers ---
#
# The synology-api package wraps SYNO.Core.FileServ.NFS.SharePrivilege only on
# the read side (and only for the global setting, not per-share rules). We use
# the per-share `load` / `save` methods directly via the session's
# request_data, following the same contract the florianehmke/synology Terraform
# provider uses. Key contract details:
#   - API:     SYNO.Core.FileServ.NFS.SharePrivilege   (version 1)
#   - load:    { share_name: <json-quoted str> } -> { share_name, rule: [...] }
#   - save:    { share_name: <json-quoted str>, rule: <json-encoded list> }
#   - save REPLACES the entire rule list; mutations must read-modify-write.
#
# Rule shape (DSM raw values):
#   { client, privilege ("ro"|"rw"), root_squash, async, crossmnt, insecure,
#     security_flavor: { sys, kerberos, kerberos_integrity, kerberos_privacy } }

_NFS_PRIVILEGE_API = "SYNO.Core.FileServ.NFS.SharePrivilege"


def _nfs_load_rules(client, share_name: str) -> list[dict[str, Any]]:
    """Read the current ordered NFS rule list for a share."""
    info = client.gen_list.get(_NFS_PRIVILEGE_API)
    if not info:
        click.echo(f"Error: DSM does not expose {_NFS_PRIVILEGE_API}", err=True)
        sys.exit(1)
    resp = client.request_data(
        _NFS_PRIVILEGE_API,
        info["path"],
        {
            "version": 1,
            "method": "load",
            "share_name": json.dumps(share_name),
        },
    )
    if not isinstance(resp, dict) or not resp.get("success"):
        click.echo(f"Error: {resp}", err=True)
        sys.exit(1)
    data = resp.get("data") or {}
    return list(data.get("rule") or [])


def _nfs_save_rules(client, share_name: str, rules: list[dict[str, Any]]) -> None:
    """Replace the NFS rule list for a share."""
    info = client.gen_list.get(_NFS_PRIVILEGE_API)
    try:
        resp = client.request_data(
            _NFS_PRIVILEGE_API,
            info["path"],
            {
                "version": 1,
                "method": "save",
                "share_name": json.dumps(share_name),
                "rule": json.dumps(rules),
            },
        )
    except Exception as e:
        code = getattr(e, "error_code", None)
        if code is not None:
            click.echo(click.style(f"Error: DSM error {code}: {e}", fg="red"), err=True)
        else:
            click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        if os.environ.get("INFRA_NAS_DEBUG"):
            click.echo(f"Payload that was sent:", err=True)
            click.echo(json.dumps(rules, indent=2), err=True)
        sys.exit(1)
    if not isinstance(resp, dict) or not resp.get("success"):
        click.echo(f"Error: {resp}", err=True)
        sys.exit(1)


def _format_rule(rule: dict[str, Any]) -> str:
    """One-line summary of a rule for display."""
    sec = rule.get("security_flavor") or {}
    sec_flags = [k for k in ("sys", "kerberos", "kerberos_integrity", "kerberos_privacy") if sec.get(k)]
    flags = []
    if rule.get("async"):
        flags.append("async")
    if rule.get("crossmnt"):
        flags.append("crossmnt")
    if rule.get("insecure"):
        flags.append("insecure")
    return (
        f"{rule.get('client', '?'):<25} "
        f"{rule.get('privilege', '?'):<3} "
        f"squash={rule.get('root_squash', '?'):<6} "
        f"sec=[{','.join(sec_flags) or '-'}] "
        f"[{','.join(flags) or '-'}]"
    )


@nas.group("nfs")
def nas_nfs():
    """Manage per-share NFS export rules."""
    pass


@nas_nfs.command("list")
@click.argument("share")
def nas_nfs_list(share: str):
    """Show NFS export rules for SHARE."""
    client = _synology_client("core_share")
    rules = _nfs_load_rules(client, share)
    if not rules:
        click.echo(f"No NFS rules configured for '{share}'.")
        return
    click.echo(f"NFS rules for '{share}' ({len(rules)} rule(s)):")
    for r in rules:
        click.echo(f"  {_format_rule(r)}")


@nas_nfs.command("debug-roundtrip")
@click.argument("share")
def nas_nfs_debug_roundtrip(share: str):
    """Save the existing rules back to SHARE unchanged (debugging only)."""
    client = _synology_client("core_share")
    rules = _nfs_load_rules(client, share)
    click.echo(f"Loaded {len(rules)} rule(s). Saving unchanged...")
    click.echo(json.dumps(rules, indent=2))
    _nfs_save_rules(client, share, rules)
    click.echo(click.style("save ok", fg="green"))


@nas.command("debug-share")
@click.argument("share")
def nas_debug_share(share: str):
    """Dump full DSM metadata for SHARE (debugging only)."""
    client = _synology_client("core_share")
    additional = [
        "hidden", "encryption", "is_aclmode", "unite_permission",
        "is_support_acl", "is_sync_share", "is_force_readonly",
        "force_readonly_reason", "recyclebin", "is_cluster_share",
        "is_exfat_share", "is_c2_share", "support_snapshot",
        "share_quota", "enable_share_compress", "enable_share_cow",
        "is_cold_storage_share", "is_missing_share", "is_offline_share",
    ]
    try:
        res = client.get_folder(share, additional=additional)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)
    click.echo(json.dumps(res, indent=2, default=str))


@nas_nfs.command("grant")
@click.argument("share")
@click.argument("client_pattern")
@click.option("--rw/--ro", "writable", default=True, help="Read-write or read-only.", show_default=True)
@click.option(
    "--root-squash",
    type=click.Choice(["root", "admin", "guest"], case_sensitive=False),
    default="root",
    show_default=True,
    help=(
        "DSM squash mode. 'root' maps uid 0 to admin (recommended for most "
        "cases); 'admin' maps everyone to admin; 'guest' maps everyone to "
        "guest. DSM does not expose a 'no_root_squash' option via this API."
    ),
)
@click.option("--async-writes/--sync-writes", "async_writes", default=True, show_default=True)
@click.option("--crossmnt/--no-crossmnt", default=True, show_default=True)
@click.option("--insecure/--secure-only", default=True, help="Allow non-privileged source ports.", show_default=True)
@click.option("--yes", "-y", is_flag=True, help="Skip the confirmation prompt.")
def nas_nfs_grant(
    share: str,
    client_pattern: str,
    writable: bool,
    root_squash: str,
    async_writes: bool,
    crossmnt: bool,
    insecure: bool,
    yes: bool,
):
    """Grant NFS access on SHARE to CLIENT_PATTERN (IP, CIDR, hostname).

    If a rule for the same client already exists, it is replaced. Other rules
    are preserved. The DSM API replaces the full rule list on save, so this
    command read-modify-writes.
    """
    client = _synology_client("core_share")
    rules = _nfs_load_rules(client, share)

    new_rule: dict[str, Any] = {
        "client": client_pattern,
        "privilege": "rw" if writable else "ro",
        "root_squash": root_squash.lower(),
        "async": async_writes,
        "crossmnt": crossmnt,
        "insecure": insecure,
        "security_flavor": {
            "sys": True,
            "kerberos": False,
            "kerberos_integrity": False,
            "kerberos_privacy": False,
        },
    }

    # Replace any existing rule for the same client; otherwise append.
    next_rules = [r for r in rules if r.get("client") != client_pattern]
    replaced = len(next_rules) != len(rules)
    next_rules.append(new_rule)

    action = "Replace" if replaced else "Add"
    click.echo(f"{action} rule on '{share}':")
    click.echo(f"  {_format_rule(new_rule)}")
    click.echo(f"({len(next_rules)} rule(s) total after save)")
    if not yes and not click.confirm("Apply?"):
        click.echo("Aborted.")
        sys.exit(0)

    _nfs_save_rules(client, share, next_rules)
    click.echo(click.style("ok", fg="green"))


@nas_nfs.command("revoke")
@click.argument("share")
@click.argument("client_pattern")
@click.option("--yes", "-y", is_flag=True, help="Skip the confirmation prompt.")
def nas_nfs_revoke(share: str, client_pattern: str, yes: bool):
    """Remove the NFS rule for CLIENT_PATTERN from SHARE."""
    client = _synology_client("core_share")
    rules = _nfs_load_rules(client, share)
    target = [r for r in rules if r.get("client") == client_pattern]
    if not target:
        click.echo(f"No rule for client '{client_pattern}' on '{share}'.")
        sys.exit(1)

    click.echo(f"Remove rule from '{share}':")
    for r in target:
        click.echo(f"  {_format_rule(r)}")
    if not yes and not click.confirm("Apply?"):
        click.echo("Aborted.")
        sys.exit(0)

    next_rules = [r for r in rules if r.get("client") != client_pattern]
    _nfs_save_rules(client, share, next_rules)
    click.echo(click.style("ok", fg="green"))


if __name__ == "__main__":
    cli()
