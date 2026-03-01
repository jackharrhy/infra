#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "click",
#     "pyyaml",
# ]
# ///
"""Infra CLI - tools for managing and visualizing infrastructure."""

from __future__ import annotations

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


if __name__ == "__main__":
    cli()
