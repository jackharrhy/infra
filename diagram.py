from diagrams import Diagram, Cluster
from diagrams.generic.compute import Rack
from diagrams.programming.language import Python, Java, Php


with Diagram("infra", show=False):
    with Cluster("DigitalOcean"):
        with Cluster("Personal"):
            Rack("macneil") << Java("macneil.club")
            Rack("muncs-craft") << Java("muncs-craft")

            cookie = Rack("cookie")
            cookie << Php("Phapbot")

        with Cluster("saturn"):
            Rack("saturn")

        with Cluster("MUNCS"):
            murray = Rack("murray") << Python("Automata")

    with Cluster("Home"):
        Rack("system76")
