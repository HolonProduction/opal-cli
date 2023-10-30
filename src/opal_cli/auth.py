import click
import opal_cli.util.bs_submit_form
import os
import os.path
import pickle
from bs4 import BeautifulSoup
from functools import update_wrapper


COOKIE_FILE = "cookies"
CREDENTIALS_FILE = "credentials"


def login_tud(session, user, pw):
    # Login link => need to press continue button to reach SSO
    res = session.get("https://bildungsportal.sachsen.de/tud")
    soup = BeautifulSoup(res.content, "html.parser")
    form = soup.select_one("form[name=form1]")
    res = form.submit(session, res.url)

    # TUD Identity Provider Login Form
    soup = BeautifulSoup(res.content, "html.parser")
    form = soup.select_one(".content > form")
    res = form.submit(session, res.url, j_username=user, j_password=pw, donotcache="0")

    # TUD IDP need to press continue button to return to Opal
    soup = BeautifulSoup(res.content, "html.parser")
    form = soup.select_one("form")
    res = form.submit(session, res.url)


@click.command()
@click.option("--sso", type=click.Choice(("tud",)), default="tud", help="Sign in solution. Currently only the TUD Indentity Provider is supported.")
@click.option("--user", "-u", type=str, default="", help="Your user name (ZIH Login).")
@click.option("--password", "-p", type=str, default="", help="Your password.")
@click.option("--logout", type=bool, is_flag=True, default=False, help="Delete persisted login information. This does not signout from the identity provider or opal. It just removes the info from you PC.")
@click.option("--persist", type=click.Choice(("off", "cookies", "credentials")), default="cookies", help="How to persist the login. \n - \"off\": No persistence. \n - \"cookies\": The session cookies are saved. The session may run out at any time. In that case you will have to relogin. \n - \"credentials\": Your password and username are stored in PLAINTEXT. You will never have to relogin.")
@click.pass_context
def auth(ctx, sso: str, user: str, password: str, logout: bool, persist: str):
    """ Manage persistent authentication for the Opal platform. Mainly useful for development purposes. """

    cookie_path = os.path.join(opal_cli.util.dirs.user_data_dir, COOKIE_FILE)
    credentials_path = os.path.join(opal_cli.util.dirs.user_data_dir, CREDENTIALS_FILE)
    os.makedirs(os.path.dirname(cookie_path), exist_ok=True)
    os.makedirs(os.path.dirname(credentials_path), exist_ok=True)

    if logout:
        if ctx.obj.authenticated_session:
            del ctx.obj["authenticated_session"]
        if os.path.exists(cookie_path):
            os.remove(cookie_path)
        if os.path.exists(credentials_path):
            os.remove(credentials_path)
        click.secho("🚪 Removed login information from your PC.", fg="green")
        return

    if ctx.obj.authenticated_session:
        click.secho("🔓 Authenticated session found.", fg="green")
        return

    session = ctx.obj.create_session()
    ctx.obj.authenticated_session = session

    if os.path.exists(cookie_path):
        click.secho("🍪 Reusing cookies.", fg="green")
        with open(cookie_path, "rb") as f:
            session.cookies.update(pickle.load(f))
        return

    if os.path.exists(credentials_path):
        click.secho("🔑 Reusing credentials.", fg="yellow")
        with open(credentials_path, "rb") as f:
            res = pickle.load(f)
        user = res["user"]
        password = res["password"]

    if not user:
        user = click.prompt("Username", type=str)
    if not password:
        password = click.prompt("Password", type=str, hide_input=True)

    match sso:
        case "tud":
            login_tud(session, user, password)

    match persist:
        case "cookies":
            click.secho("🍪 Saving session cookies.", fg="yellow")
            with open(cookie_path, "wb") as f:
                pickle.dump(session.cookies, f)
        case "credentials":
            click.echo(click.style("🔑 Saving credentials in ", fg="red")+click.style('plaintext', bold=True, fg="red")+click.style(". Use \"opal auth --logout\" to remove them.", fg="red"))
            with open(credentials_path, "wb") as f:
                pickle.dump({"password": password, "user": user}, f)


def with_session(login: bool = True):
    def decorator(f):
        @click.pass_context
        def wrapper(ctx, *args, **kwargs):
            if login:
                if not ctx.obj.authenticated_session:
                    ctx.invoke(auth, persist=False)
                session = ctx.obj.authenticated_session
            else:
                session = ctx.obj.create_session()
            return ctx.invoke(f, session, *args, **kwargs)
        return update_wrapper(wrapper, f)
    return decorator
