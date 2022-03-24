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
            muncs_craft = Server("muncs-craft")
            muncs_craft << Java("muncs-craft")

            with Cluster("cookie"):
                cookie = Server("cookie")
                tailscale << cookie

                cookie_docker = Docker("docker")
                cookie << cookie_docker

                with Cluster("jackharrhy.com"):
                    jackharrhy = Nginx("jackharrhy.com")
                    jackharrhy << WebSite("jackharrhy.com")
                    jackharrhy << WebSite("harrhy.xyz")
                    jackharrhy << WebSite("jackharrhy.dev")
                    cookie_docker << jackharrhy

                strickertrade = Remix("stickertrade")
                strickertrade << WebSite("stickertrade.ca")
                cookie_docker << strickertrade

                livebook = Elixir("livebook")
                livebook << WebSite("livebook.jackharrhy.dev")
                cookie_docker << livebook

                bar = Python("bar")
                bar << WebSite("jackharrhy.dev/bar")
                cookie_docker << bar

                barab = JavaScript("barab")
                barab << WebSite("jackharrhy.dev/barab")
                cookie_docker << barab

                duaas = Rust("duaas")
                duaas << WebSite("jackharrhy.dev/random")
                cookie_docker << duaas

                stackcoin = Crystal("stackcoin")
                stackcoin << WebSite("stackcoin.world")
                cookie_docker << stackcoin

                phapbot = Php("Phapbot")
                cookie_docker << phapbot

                with Cluster("miniflux"):
                    miniflux = Go("miniflux")
                    miniflux << WebSite("miniflux.jackharrhy.dev")
                    cookie_docker << miniflux

                    miniflux_db = PostgreSQL("miniflux_db")
                    miniflux << miniflux_db
                    cookie_docker << miniflux_db

                traefik = Go("Traefik")
                cookie_docker << traefik

                watchtower = Go("Watchtower")
                cookie_docker << watchtower

        with Cluster("MUNCS"):
            murray = Server("murray")
            murray << Python("Automata")
            murray << Python("DiscordAuth")

    with Cluster("Home"):
        stash = Storage("stash")
        tailscale << stash

        cardiff = Laptop("cardiff")
        tailscale << cardiff

        windows = Desktop("windows")
        tailscale << windows

    lemur = Laptop("lemur")
    tailscale << lemur

    pixel = CellPhone("pixel")
    tailscale << pixel
