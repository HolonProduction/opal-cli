import requests
import logging
import click

import urllib.parse

import http.client
from bs4 import BeautifulSoup, Tag
import pickle
import sys
import getpass

from opal_cli.util import ContextObject
from opal_cli.auth import auth 
from opal_cli.deadlines import deadlines


def setup_logging():
    http.client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


@click.group(help="Slighly overengineered CLI solution to prevent visiting the OPAL Website.")
@click.pass_context
def opal_cli(ctx):
    def create_session() -> requests.Session:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0"})

        # Set Opal cookie to use desktop site
        opal_url = "https://bildungsportal.sachsen.de/opal/wicket/bookmarkable/de.bps.olat.gui.page.mobile.MobileDetectionPage/Fajax=true?continue=true&amp;mobile=false"
        res = session.get(opal_url)

        return session

    ctx.obj = ContextObject(create_session)


def main():
    opal_cli.add_command(auth)
    opal_cli.add_command(deadlines)
    opal_cli()


if __name__ == "__main__":
    main()
