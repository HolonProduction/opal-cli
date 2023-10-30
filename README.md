# :gem: opal-cli

> This project is in no way associated with Opal or Bildungsportal Sachsen GmbH. It is only meant for educational purposes. Use at your own discretion.

## What is this?
This is a cli application to interact with the Opal Learning Platform. Is it powered by webscraping techniques.

## Isn't there an API?
There is. But it has to be unlocked on a per user basis, which only seems to happen for university projects.

---

## Available commands

Use `--help` for more details.

### `auth`
Manage persistent login. Mainly used for development. The other commands will ask for credentials if you aren't logged in. 

> Note that Opal will only allow a certain amount of active sessions per user, so it might ask you to relogin after using `opal-cli`. Don't interact with the Opal website while the cli is running.

### `deadlines`
Go through your courses and export deadlines for quizes and file uploads into an `ics` file.
