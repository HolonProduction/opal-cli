import click
from typing import Iterable, Any, IO
from opal_cli.auth import with_session
from opal_cli.util.ajax import get_ajax_base_url
from requests import Session
from bs4 import BeautifulSoup, Tag
import re
import urllib.parse
from urllib.parse import urlparse, urlunparse
import json
import time
from datetime import datetime
from icalendar import Todo, Event, Calendar
import uuid


def make_uuid(random_uuids: bool, uuid_namespace: str, uuid_offset: int, url: str) -> uuid.UUID:
    if random_uuids:
        return uuid.uuid4()
    else:
        return uuid.uuid5(uuid.UUID(uuid_namespace), url + str(uuid_offset))


UNTIL_DEADLINE_REGEX = re.compile(R"bis\s*(?P<day>[0-9]+)\.(?P<month>[0-9]+)\.(?P<year>[0-9]+)\s*(?P<hour>[0-9]+):(?P<minutes>[0-9]+)\s*Uhr")
DEADLINE_REGEX = re.compile(R"start|abgeben", re.I)
def extract_from_access_box(box: Tag, url: str, random_uuids: bool, uuid_namespace: str) -> Iterable[Event]:
    uuid_offset = 0

    content = box.select_one(".box-content")
    if content: # Not yet unlocked format
        for li in content.find_all("li"):
            m = UNTIL_DEADLINE_REGEX.search(li.text)
            if m:
                ev = Event()
                ev.add("uid", make_uuid(random_uuids, uuid_namespace, uuid_offset, url))
                ev.add("dtstart", datetime(
                    int(m.group("year")), 
                    int(m.group("month")), 
                    int(m.group("day")), 
                    int(m.group("hour")), 
                    int(m.group("minutes")),
                ))
                ev.add("url", url)
                yield(ev)
                uuid_offset += 1
        return

    content = box.select_one(".box-access-content")
    if content: # Already unlocked format
        for ul in content.find_all("ul"):   
            if DEADLINE_REGEX.search(next(ul.previous_siblings).text):
                m = UNTIL_DEADLINE_REGEX.search(ul.text)
                if m:
                    ev = Event()
                    ev.add("uid", make_uuid(random_uuids, uuid_namespace, uuid_offset, url))
                    ev.add("dtstart", datetime(
                        int(m.group("year")), 
                        int(m.group("month")), 
                        int(m.group("day")), 
                        int(m.group("hour")), 
                        int(m.group("minutes")),
                    ))
                    ev.add("url", url)
                    yield(ev)
                    uuid_offset += 1
        return

    click.secho(f"❌ Unknown access box format at '{url}'. Please report.", fg="red")


def extract_from_task(session: Session, url: str, random_uuids: bool, uuid_namespace: str) -> Iterable[Event]:
    res = session.get(url)
    soup = BeautifulSoup(res.content, "html.parser")
    
    access = soup.select_one(".box-access")
    if access:
        yield from extract_from_access_box(access, url, random_uuids, uuid_namespace)
        return

    # The access box may be hidden behind an ajax request
    u = urlparse(url)
    relative_url = urlunparse(("", "", u.path, u.params, u.query, u.fragment))
    regex = re.compile(R'"(?P<url>' + relative_url + R'\?[0-9]+-[0-9]+.[0-9]+-)"')
    m = regex.search(res.content.decode("utf-8"))
    if not m:
        click.secho(f"❌ Could not find box with access information at '{url}'.", fg="red")
        return

    relative_url = m.group("url")
    # HACK: Add timestamp to the ajax url. Can't use urllib parse to add a new query string since it would drop the request quantifiers.
    u = urllib.parse.urljoin(url, relative_url) + f"&_={str(round(time.time()*1000))}"
    res = session.get(u, headers={
        "Wicket-Ajax": "true",
        "Wicket-Ajax-BaseURL": get_ajax_base_url(res.content.decode("utf-8")),
    })
    soup = BeautifulSoup(res.content, "xml")
    
    # The ajax request results in multiple components. We don't know which one contains the access box.

    found = False

    for con in soup.find_all("component"):
        sub_soup = BeautifulSoup(str(con.text), "html.parser")
        access = sub_soup.select_one(".box-access")
        if access:
            yield from extract_from_access_box(access, url, random_uuids, uuid_namespace)
            found = True
    
    if not found:
        click.secho(f"❌ Could not find box with access information at '{url}'.", fg="red")


NODES_WITH_DEADLINE_REGEX = re.compile(R'a_attr":(?P<json>{("[^"]*":"[^"]*",?)*?"class":"[^"]*(node-iqtest|node-ta)[^"]*"})')
def extract_from_course(session: Session, url: str, random_uuids: bool, uuid_namespace: str) -> Iterable[Event]:
    res = session.get(url)
    soup = BeautifulSoup(res.content, "html.parser")
    
    click.echo(click.style("🎓 Found Course: ", fg="green") + click.style(soup.h1.text.strip(), bold=True, fg="green"))

    # The sidebar is embedded in json and rendered dynamically. Uses regex to find the json entries.
    for i in NODES_WITH_DEADLINE_REGEX.finditer(res.content.decode("utf-8")):
        data = json.loads(i.group("json"))
        click.echo(click.style("\t ✏️ Found Task: ", fg="green") + click.style(data["title"], fg="green", bold=True))
        for ev in extract_from_task(session, data["href"], random_uuids, uuid_namespace):
            ev.add("summary",  f"{soup.h1.text.strip()}: {data['title']}")
            yield ev


@click.command()
@click.option("--random-uuids/--const-uuids", " /-c", type=bool, default=True, help="Whether to use random uuids for the calender events or uuids based on the task url. Constant urls may allow updating a calendar but also contain identifiable information.")
@click.option("--uuid-namespace", type=str, default="e375416e-f30e-4e27-be98-9cbc7c6a09d6", help="Uuid namespace for constant uuids.")
@click.option("--todo/--event", type=bool, is_flag=True, default=False, show_default="event", help="Whether to save deadlines as VEVENT or VTODO. Todo might be more descriptive but not all programms recognize it.")
@click.argument("file", type=click.File("wb", atomic=True))
@with_session()
def deadlines(session: Session, file: IO[Any], random_uuids: bool, uuid_namespace: str, todo: bool):
    """ Goes through your courses and searches for quizes and upload asignments. Saves deadlines for those into an ics file. """

    res = session.get("https://bildungsportal.sachsen.de/opal/auth/resource/courses/Fajax=true")
    soup = BeautifulSoup(res.content, "html.parser")

    # TODO: Extract routine checks
    if ("Sie sind nicht mehr in der Lernplattform angemeldet. Bitte loggen Sie sich erneut ein." in str(soup.body)) or ("Wir ermitteln Ihren Browser." in str(soup.body)):
        click.secho("Session not valid anymore. Use opal auth --logout", fg="red")
        return

    if ("Bitte melden Sie sich an." in str(soup.body)):
        click.echo("Wrong credentials.")
        return

    click.secho("🔎 Searching for courses and their tasks.", fg="yellow")

    cal = Calendar()

    for link in soup.select("form ul li a"):
        if link.get("title") == "Course open" or link.get("title") == "Kurs öffnen":
            for ev in extract_from_course(session, link.get("href"), random_uuids, uuid_namespace):
                if todo:
                    ev.name = Todo.name
                cal.add_component(ev)
    
    file.write(cal.to_ical())
