import os
import random
import sqlite3
import time
import urllib

import flask
from bcrypt import checkpw
from flask import current_app, g, redirect, render_template, request, url_for

from .config import load_config

app = flask.Flask(__name__)


def authenticate(username, password):
    return username == current_app.config["admin_username"] and check_password(
        password, current_app.config
    )


def check_long_exist(long):
    query = query_db("SELECT short FROM urls WHERE long = ?", (long,))
    for i in query:
        if (
            i
            and (len(i["short"]) <= current_app.config["random_length"])
            and i["short"] != current_app.config["latest"]
        ):  # Checks if query if pre-existing URL is same as random length URL
            return i["short"]
    return False


def check_short_exist(short):  # Allow to also check against a long link
    if get_long(short):
        return True
    return False


def linking_to_blocklist(long):
    # Removes protocol and other parts of the URL to extract the domain name
    long = long.split("//")[-1].split("/")[0]
    if long in current_app.config["blocklist"]:
        return True
    if not current_app.config["selflinks"]:
        return long in get_baseUrl()
    return False


def check_password(password, pass_config):
    if pass_config["password_hashed"]:
        return checkpw(
            password.encode("utf-8"),
            pass_config["admin_hashed_password"].encode("utf-8"),
        )
    elif not pass_config["password_hashed"]:
        return password == pass_config["admin_password"]
    else:
        raise RuntimeError("This should never occur! Bailing...")


def delete_short(deletion):
    result = query_db(
        "SELECT * FROM urls WHERE short = ?", (deletion,), False, None
    )  # Return as tuple instead of row
    get_db().cursor().execute("DELETE FROM urls WHERE short = ?", (deletion,))
    get_db().commit()
    return len(result)


def delete_long(long):
    if "//" in long:
        long = long.split("//")[-1]
    long = "%" + long + "%"
    result = query_db(
        "SELECT * FROM urls WHERE long LIKE ?", (long,), False, None
    )  # Return as tuple instead of row
    get_db().cursor().execute("DELETE FROM urls WHERE long LIKE ?", (long,))
    get_db().commit()
    return len(result)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def generate_short(rq):
    timeout = time.time() + current_app.config["random_gen_timeout"]
    while True:
        if time.time() >= timeout:
            return response(rq, None, "Timeout while generating random short URL")
        short = "".join(
            random.choice(current_app.config["allowed_chars"])
            for i in range(current_app.config["random_length"])
        )
        if not check_short_exist(short) and short != app.config["latest"]:
            return short


def get_long(short):
    row = query_db("SELECT long FROM urls WHERE short = ?", (short,), True)
    if row and row["long"]:
        return row["long"]
    return None


def get_baseUrl():
    if current_app.config["site_domain"]:
        # TODO: un-hack-ify adding the protocol here
        return "https://" + current_app.config["site_domain"] + "/"
    else:
        return request.base_url


def list_shortlinks():
    result = query_db("SELECT * FROM urls", (), False, None)
    result = nested_list_to_dict(result)
    return result


def nested_list_to_dict(l):
    d = {}
    for nl in l:
        d[nl[0]] = nl[1]
    return d


def response(rq, result, error_msg="Error: Unknown error"):
    if rq.form.get("api"):
        if rq.accept_mimetypes.accept_json:
            if result:
                return flask.jsonify(success=bool(result), result=result)
            return flask.jsonify(success=bool(result), message=error_msg)
        else:
            return "Format type HTML (default) not supported for API"  # Future-proof for non-json return types
    else:
        if result and result is not True:
            flask.flash(result, "success")
        elif not result:
            flask.flash(error_msg, "error")
        return render_template("main.html")


def set_latest(long):
    if app.config["latest"]:
        if query_db(
            "SELECT short FROM urls WHERE short = ?", (current_app.config["latest"],)
        ):
            get_db().cursor().execute(
                "UPDATE urls SET long = ? WHERE short = ?",
                (long, current_app.config["latest"]),
            )
        else:
            get_db().cursor().execute(
                "INSERT INTO urls (long,short) VALUES (?, ?)",
                (long, current_app.config["latest"]),
            )


def validate_short(short):
    if short == app.config["latest"]:
        return response(
            request,
            None,
            "Short URL cannot be the same as a special URL ({})".format(short),
        )
    for char in short:
        if char not in current_app.config["allowed_chars"]:
            return response(
                request, None, "Character " + char + " not allowed in short URL"
            )
    return True


def validate_long(long):  # https://stackoverflow.com/a/36283503
    token = urllib.parse.urlparse(long)
    return all([token.scheme, token.netloc])


# Database connection functions


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            "".join((current_app.config["database_name"], ".db")),
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.cursor().execute("CREATE TABLE IF NOT EXISTS urls (long,short)")
    return g.db


def query_db(query, args=(), one=False, row_factory=sqlite3.Row):
    get_db().row_factory = row_factory
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, "sqlite_db"):
        g.sqlite_db.close()


app.config.update(load_config())  # Add YAML config to Flask config
app.secret_key = app.config["secret_key"]
app.config["SERVER_NAME"] = app.config["site_domain"]


@app.route("/favicon.ico", subdomain=app.config["subdomain"])
def favicon():
    return flask.send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/", subdomain=app.config["subdomain"])
def main():
    return response(request, True)


@app.route("/<url>")
def main_redir(url):
    long = get_long(url)
    if long:
        resp = flask.make_response(flask.redirect(long, 301))
    else:
        flask.flash('Short URL "' + url + "\" doesn't exist", "error")
        resp = flask.make_response(flask.redirect(url_for("main")))
    resp.headers.set("Cache-Control", "no-store, must-revalidate")
    return resp


@app.route("/", methods=["POST"], subdomain=app.config["subdomain"])
def main_post():
    if request.form.get("api"):
        if current_app.config["disable_api"]:
            return response(request, None, "API is disabled.")
        # All API calls require authentication
        if not request.authorization or not authenticate(
            request.authorization["username"], request.authorization["password"]
        ):
            return response(request, None, "BaiscAuth failed")
        command = request.form["api"]
        if command == "list" or command == "listshort":
            return response(request, list_shortlinks(), "Failed to list items")
        elif command == "listlong":
            shortlinks = list_shortlinks()
            shortlinks = {v: k for k, v in shortlinks.items()}
            return response(request, shortlinks, "Failed to list items")
        elif command == "delete":
            deleted = 0
            if "long" not in request.form and "short" not in request.form:
                return response(request, None, "Provide short or long in POST data")
            if "short" in request.form:
                deleted = delete_short(request.form["short"]) + deleted
            if "long" in request.form:
                deleted = delete_long(request.form["long"]) + deleted
            if deleted > 0:
                return response(
                    request,
                    "Deleted " + str(deleted) + " URL" + ("s" if deleted > 1 else ""),
                )
            else:
                return response(request, None, "URL not found")
        else:
            return response(request, None, "Command " + command + " not found")

    if request.form.get("long"):
        if not validate_long(request.form["long"]):
            return response(request, None, "Long URL is not valid")
        if request.form.get("short"):
            # Validate long as URL and short custom text against allowed characters
            result = validate_short(request.form["short"])
            if validate_short(request.form["short"]) is True:
                short = request.form["short"]
            else:
                return result
            if get_long(short) == request.form["long"]:
                return response(
                    request,
                    get_baseUrl() + short,
                    "Error: Failed to return pre-existing non-random shortlink",
                )
        else:
            short = generate_short(request)
        if check_short_exist(short):
            return response(request, None, "Short URL already taken")
        long_exists = check_long_exist(request.form["long"])
        if linking_to_blocklist(request.form["long"]):
            return response(request, None, "You cannot link to this site")
        if long_exists and not request.form.get("short"):
            set_latest(request.form["long"])
            get_db().commit()
            return response(
                request,
                get_baseUrl() + long_exists,
                "Error: Failed to return pre-existing random shortlink",
            )
        get_db().cursor().execute(
            "INSERT INTO urls (long,short) VALUES (?,?)", (request.form["long"], short)
        )
        set_latest(request.form["long"])
        get_db().commit()
        return response(request, get_baseUrl() + short, "Error: Failed to generate")
    else:
        return response(request, None, "Long URL required")


if __name__ == "__main__":
    app.run()
