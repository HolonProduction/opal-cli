from typing import Callable
from requests import Session

from appdirs import AppDirs
import urllib


dirs = AppDirs("opal-cli", "HolonProduction")


class ContextObject:
    create_session: Callable = None
    authenticated_session: Session = None

    def __init__(self, create_session: Callable):
        self.create_session = create_session
