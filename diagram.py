from diagrams import Diagram, Cluster
from diagrams.onprem.compute import Server
from diagrams.programming.language import (
    Python,
    Java,
    Php,
    Rust,
    JavaScript,
    Go,
    Elixir,
)
from diagrams.generic.storage import Storage
from diagrams.generic.blank import Blank
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.container import Docker
from diagrams.onprem.network import Nginx
from diagrams.custom import Custom


class WebSite(Custom):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, "./images/web.png", *args, **kwargs)


class Crystal(Custom):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, "./images/crystal.png", *args, **kwargs)


class Remix(Custom):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, "./images/remix.png", *args, **kwargs)


class Tailscale(Custom):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, "./images/tailscale.png", *args, **kwargs)


class Desktop(Custom):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, "./images/desktop.png", *args, **kwargs)


class Laptop(Custom):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, "./images/laptop.png", *args, **kwargs)


class CellPhone(Custom):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, "./images/cellphone.png", *args, **kwargs)


with Diagram("infra", show=False, direction="TB"):
    tailscale = Tailscale("Tailscale")

    with Cluster("DigitalOcean"):
        with Cluster("Personal"):
            with Cluster("mug"):
                mug = Server("mug")
                tailscale << mug

                mug_docker = Docker("docker")
                mug << mug_docker

                with Cluster("jackharrhy.com"):
                    jackharrhy = Nginx("jackharrhy.com")
                    jackharrhy << WebSite("jackharrhy.com")
                    jackharrhy << WebSite("harrhy.xyz")
                    jackharrhy << WebSite("jackharrhy.dev")
                    mug_docker << jackharrhy

                strickertrade = Remix("stickertrade")
                strickertrade << WebSite("stickertrade.ca")
                mug_docker << strickertrade

                livebook = Elixir("livebook")
                livebook << WebSite("livebook.jackharrhy.dev")
                mug_docker << livebook

                bar = Python("bar")
                bar << WebSite("jackharrhy.dev/bar")
                mug_docker << bar

                barab = JavaScript("barab")
                barab << WebSite("jackharrhy.dev/barab")
                mug_docker << barab

                duaas = Rust("duaas")
                duaas << WebSite("jackharrhy.dev/random")
                mug_docker << duaas

                stackcoin = Crystal("stackcoin")
                stackcoin << WebSite("stackcoin.world")
                mug_docker << stackcoin

                phapbot = Php("Phapbot")
                mug_docker << phapbot

                with Cluster("miniflux"):
                    miniflux = Go("miniflux")
                    miniflux << WebSite("miniflux.jackharrhy.dev")
                    mug_docker << miniflux

                    miniflux_db = PostgreSQL("miniflux_db")
                    miniflux << miniflux_db
                    mug_docker << miniflux_db

                traefik = Go("Traefik")
                mug_docker << traefik

                watchtower = Go("Watchtower")
                mug_docker << watchtower

        with Cluster("MUNCS"):
            murray = Server("murray")
            murray << Python("Automata")
            murray << Python("DiscordAuth")

    with Cluster("Home"):
        stash = Storage("stash")
        tailscale << stash

        windows = Desktop("windows")
        tailscale << windows

    lemur = Laptop("lemur")
    tailscale << lemur

    pixel = CellPhone("pixel")
    tailscale << pixel
