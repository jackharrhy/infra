from diagrams import Diagram, Cluster
from diagrams.onprem.compute import Server
from diagrams.programming.language import (
    Python,
    Php,
    Rust,
    JavaScript,
    Go,
    Elixir,
)
from diagrams.generic.storage import Storage
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
                    jackharrhy << WebSite("jackharrhy.dev")
                    jackharrhy << WebSite("harrhy.xyz")
                    jackharrhy << WebSite("jack.harrhy.xyz")
                    jackharrhy << WebSite("jack.arthur.harrhy.xyz")
                    jackharrhy << WebSite("jack.is.harrhy.xyz")
                    mug_docker << jackharrhy

                siliconharbour = JavaScript("siliconharbour")
                siliconharbour << WebSite("siliconharbour.dev")
                mug_docker << siliconharbour

                plow = Python("where-the-plow")
                plow << WebSite("plow.jackharrhy.dev")
                mug_docker << plow

                notscared = JavaScript("notscared-site")
                notscared << WebSite("notsca.red")
                mug_docker << notscared

                burger = JavaScript("burger")
                burger << WebSite("big.burger.beauty")
                mug_docker << burger

                rotund = Nginx("rotund.org")
                rotund << WebSite("rotund.org")
                mug_docker << rotund

                andrew_astro = JavaScript("andrewsite-astro")
                andrew_astro << WebSite("andrewgossecomposer.com")
                mug_docker << andrew_astro

                andrew_strapi = JavaScript("andrewsite-strapi")
                andrew_strapi << WebSite("api.andrewgossecomposer.com")
                mug_docker << andrew_strapi

                sluggers = JavaScript("sluggers-super-draft")
                sluggers << WebSite("lil-slug-crew.jackharrhy.dev")
                mug_docker << sluggers

                sluggers_db = PostgreSQL("sluggers_super_draft_db")
                sluggers << sluggers_db
                mug_docker << sluggers_db

                almanac = Remix("almanac")
                almanac << WebSite("almanac.jackharrhy.dev")
                mug_docker << almanac

                steve = Python("letters-to-steve")
                steve << WebSite("steve-letter-writ.ing")
                mug_docker << steve

                stickertrade = Remix("stickertrade")
                stickertrade << WebSite("stickertrade.ca")
                mug_docker << stickertrade

                bar = Python("bar")
                bar << WebSite("jackharrhy.dev/bar")
                mug_docker << bar

                duaas = Rust("duaas")
                duaas << WebSite("jackharrhy.dev/urandom")
                mug_docker << duaas

                stackcoin = Crystal("stackcoin")
                stackcoin << WebSite("stackcoin.world")
                mug_docker << stackcoin

                incydecy = JavaScript("incydecy")
                mug_docker << incydecy

                phapbot = Php("phapbot")
                mug_docker << phapbot

                with Cluster("miniflux"):
                    miniflux = Go("miniflux")
                    miniflux << WebSite("miniflux.jackharrhy.dev")
                    mug_docker << miniflux

                    miniflux_db = PostgreSQL("miniflux_db")
                    miniflux << miniflux_db
                    mug_docker << miniflux_db

                beszel = Go("beszel")
                beszel << WebSite("beszel.jackharrhy.dev")
                mug_docker << beszel

                beszel_agent = Go("beszel-agent")
                beszel << beszel_agent
                mug_docker << beszel_agent

                traefik = Go("traefik")
                mug_docker << traefik

                watchtower = Go("watchtower")
                mug_docker << watchtower

                livebook = Elixir("livebook")
                livebook << WebSite("livebook.jackharrhy.dev")
                mug_docker << livebook

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
