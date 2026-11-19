#!/usr/bin/env python3
# %% [markdown]
# # Lesson 6: Logins, sessions and forms
#
# Some content only appears after you log in or submit a form. To scrape
# it, your code has to do what a browser does behind the scenes:
#
# 1. **GET** the page with the form.
# 2. Collect **every** field the form will send, including hidden ones such
#    as CSRF tokens.
# 3. **POST** the form.
# 4. Keep the **cookies** the server sets, so later requests stay logged in.
#
# We'll practise on https://quotes.toscrape.com/login (any username and
# password works) and on an ASP.NET-style search form.
#
# > **Only log in to accounts that are yours, and check the site's terms.**
# > Scraping behind a login is often explicitly forbidden, and you are
# > responsible for what your account does.

# %%
import json
import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)
SITE = "https://quotes.toscrape.com"
HEADERS = {
    "User-Agent": "web-scraping-with-python tutorial "
    "(+https://github.com/rajat4665/web-scraping-with-python)"
}

# %% [markdown]
# ## 1. Look at the form
#
# Inspect the login form and you'll find three inputs, one of them hidden:
#
# ```html
# <form action="/login" method="post">
#   <input type="hidden" name="csrf_token" value="AbCdEf...">
#   <input type="text" name="username">
#   <input type="password" name="password">
# </form>
# ```
#
# The `csrf_token` is a random value the server puts in the form and checks
# when you submit it. It proves the form came from the site itself
# (protection against *Cross-Site Request Forgery*). Real sites reject a
# login without the correct token, so you must read it from the page first.
#
# This helper collects the default values of **all** fields in a form, so
# hidden fields are never forgotten:


# %%
def form_fields(form):
    """Return {name: value} for every field in a <form>, as a browser would send it."""
    data = {}
    for field in form.find_all(["input", "select", "textarea"]):
        name = field.get("name")
        if not name or field.get("type") in ("submit", "button", "image", "file"):
            continue
        if field.get("type") in ("checkbox", "radio") and not field.has_attr("checked"):
            continue
        if field.name == "select":
            option = field.find("option", selected=True) or field.find("option")
            data[name] = option.get("value", option.get_text()) if option else ""
        elif field.name == "textarea":
            data[name] = field.get_text()
        else:
            data[name] = field.get("value", "")
    return data


session = requests.Session()
session.headers.update(HEADERS)

login_page = session.get(f"{SITE}/login", timeout=15)
form = BeautifulSoup(login_page.content, "html.parser").find("form")
print("Form action:", form["action"], "| method:", form.get("method"))
print("Fields:", form_fields(form))
print("Cookies so far:", session.cookies.get_dict())

# %% [markdown]
# Notice that the server already set a `session` cookie. The CSRF token is
# tied to it, which is why you must use the **same** `Session` for the GET
# and the POST.

# %% [markdown]
# ## 2. Log in
#
# **Never put real passwords in your code** (and never commit them to
# git). Read them from environment variables, or ask for them with
# `getpass`. This practice site accepts anything, so we fall back to a
# dummy value.


# %%
def get_credentials():
    username = os.environ.get("SCRAPER_USERNAME", "student")
    password = os.environ.get("SCRAPER_PASSWORD")
    if password is None:
        # In a real project, ask for it instead:
        #     import getpass
        #     password = getpass.getpass("Password: ")
        password = "any-password-works-here"
    return username, password


def login(session, username, password):
    page = session.get(f"{SITE}/login", timeout=15)
    form = BeautifulSoup(page.content, "html.parser").find("form")
    data = form_fields(form)  # includes csrf_token
    data.update(username=username, password=password)

    response = session.post(f"{SITE}{form['action']}", data=data, timeout=15)
    response.raise_for_status()

    # Always check that it worked: many sites answer 200 even on failure.
    soup = BeautifulSoup(response.content, "html.parser")
    if not soup.find("a", href="/logout"):
        error = soup.select_one(".error, .alert-danger")
        reason = error.get_text(strip=True) if error else "unknown reason"
        raise RuntimeError(f"Login failed: {reason}")
    return response


response = login(session, *get_credentials())
print("Logged in! Landed on:", response.url)
print("Cookies now:", list(session.cookies.get_dict()))

# %% [markdown]
# ## 3. Content only logged-in users see
#
# On this site, logged-in users get a "(Goodreads page)" link for each
# author. Let's compare a logged-out session with ours.


# %%
def goodreads_links(sess):
    soup = BeautifulSoup(sess.get(SITE, timeout=15).content, "html.parser")
    return [a["href"] for a in soup.find_all("a", string="(Goodreads page)")]


anonymous = requests.Session()
anonymous.headers.update(HEADERS)
print("Logged out:", len(goodreads_links(anonymous)), "Goodreads links")
links = goodreads_links(session)
print("Logged in: ", len(links), "Goodreads links, e.g.", links[0])

# %% [markdown]
# ## 4. Save cookies and reuse them later
#
# Logging in on every run is slow, and some sites flag repeated logins.
# Save the cookies to a file and load them next time. Treat that file like
# a password: anyone who has it is logged in as you.

# %%
cookie_file = OUTPUT / "cookies.json"
cookie_file.write_text(json.dumps(session.cookies.get_dict()))

new_session = requests.Session()
new_session.headers.update(HEADERS)
new_session.cookies.update(json.loads(cookie_file.read_text()))
print("Fresh session with saved cookies sees", len(goodreads_links(new_session)), "Goodreads links")

# %% [markdown]
# Cookies expire. A robust scraper checks whether it's still logged in and
# calls `login()` again if not.

# %% [markdown]
# ## 5. Multi-step forms with hidden state (ASP.NET `__VIEWSTATE`)
#
# Older ASP.NET sites keep the page's state in a large hidden field called
# `__VIEWSTATE`, and each step of a form depends on the previous one. Open
# https://quotes.toscrape.com/search.aspx:
#
# 1. Choose an **author**. The page reloads with that author's **tags**.
# 2. Choose a **tag** and search.
#
# Every POST must send back the `__VIEWSTATE` from the *previous* response.
# Our `form_fields()` helper takes care of that automatically.


# %%
def search_quotes(author, tag):
    s = requests.Session()
    s.headers.update(HEADERS)

    # Step 1: load the form
    soup = BeautifulSoup(s.get(f"{SITE}/search.aspx", timeout=15).content, "html.parser")
    authors = [o["value"] for o in soup.select("select#author option") if o.get("value")]
    print(f"{len(authors)} authors available")

    # Step 2: pick the author; the response contains that author's tags
    data = form_fields(soup.form)
    data["author"] = author
    response = s.post(f"{SITE}/filter.aspx", data=data, timeout=15)
    soup = BeautifulSoup(response.content, "html.parser")
    tags = [o["value"] for o in soup.select("select#tag option") if o.get("value")]
    print(f"Tags for {author}: {tags}")

    # Step 3: pick a tag and submit (with the NEW __VIEWSTATE)
    data = form_fields(soup.form)
    data.update(author=author, tag=tag, submit_button="Search")
    response = s.post(f"{SITE}/filter.aspx", data=data, timeout=15)
    soup = BeautifulSoup(response.content, "html.parser")
    return [
        {
            "author": q.select_one("span.author").get_text(strip=True),
            "text": q.select_one("span.content").get_text(strip=True),
            "tag": q.select_one("span.tag").get_text(strip=True),
        }
        for q in soup.select("div.quote")
    ]


for quote in search_quotes("Albert Einstein", "world"):
    print(quote)

# %% [markdown]
# ## Troubleshooting logins
#
# * **The login "works" but you're not logged in:** compare your request with
#   the browser's in DevTools → Network → the POST request → **Payload**.
#   Are any fields missing?
# * **`403` or "invalid token":** you probably used a different session for
#   the GET and the POST, or reused an old token.
# * **The login form is built with JavaScript, or there's a CAPTCHA:** the
#   site doesn't want automated logins. Look for an official API instead.
#   (Playwright from Lesson 5 can fill forms, but bypassing a CAPTCHA is
#   circumventing a protection. Don't.)
# * **Some sites send JSON instead of a form:** check the request's
#   Content-Type in DevTools and use `session.post(url, json=...)`.
#
# **Next:** [Lesson 7: Scrapy](07_scrapy_framework.ipynb)
