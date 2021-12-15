from diagrams import Diagram, Cluster
from diagrams.onprem.compute import Server
from diagrams.programming.language import Python, Java, Php, Rust, JavaScript, Go, Elixir
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

with Diagram("infra", show=False, direction="TB"):
    with Cluster("DigitalOcean"):
        with Cluster("Personal"):
            macneil = Server("macneil")
            macneil << Java("macneil.club")

            muncs_craft = Server("muncs-craft")
            muncs_craft << Java("muncs-craft")

            with Cluster("cookie"):
                cookie = Server("cookie")
                cookie_docker = Docker("docker")
                cookie << cookie_docker

                with Cluster("jackharrhy.com"):
                    jackharrhy = Nginx("jackharrhy.com")
                    jackharrhy << WebSite("jackharrhy.com")
                    jackharrhy << WebSite("harrhy.xyz")
                    jackharrhy << WebSite("jackharrhy.dev")
                    cookie_docker << jackharrhy

                pad = Crystal("pad")
                pad << WebSite("pad.jackharrhy.dev")
                cookie_docker << pad

                livebook = Elixir("livebook")
                livebook << WebSite("livebook.jackharrhy.dev")
                cookie_docker << livebook

                cbcrss = Crystal("cbcrss")
                cbcrss << WebSite("cbc-rss.jackharrhy.dev")
                cookie_docker << cbcrss

                barab = JavaScript("barab")
                barab << WebSite("jackharrhy.dev/barab")
                cookie_docker << barab

                duaas = Rust("duaas")
                duaas << WebSite("jackharrhy.dev/random")
                cookie_docker << duaas

                bar = Python("bar")
                bar << WebSite("jackharrhy.dev/bar")
                cookie_docker << bar

                metrobus_spy = Python("metrobus-spy")
                metrobus_spy << WebSite("jackharrhy.dev/metrobus-spy")
                cookie_docker << metrobus_spy

                stackcoin = Crystal("stackcoin")
                stackcoin << WebSite("stackcoin.world")
                cookie_docker << stackcoin

                with Cluster("miniflux"):
                    miniflux = Go("miniflux")
                    miniflux << WebSite("miniflux.jackharrhy.dev")
                    cookie_docker << miniflux

                    miniflux_db = PostgreSQL("miniflux_db")
                    miniflux << miniflux_db
                    cookie_docker << miniflux_db

                phapbot = Php("Phapbot")
                cookie_docker << phapbot

        with Cluster("saturn"):
            Server("saturn")

        with Cluster("MUNCS"):
            murray = Server("murray")
            murray << Python("Automata")
            murray << Python("DiscordAuth")

    with Cluster("Home"):
        system76 = Server("system76")
        system76 << Java("cheesetown")

        stash = Storage("stash")
