# Copyright (c) 2019 Steven Spangler <132@ikl.sh>
# This file is part of liteshort by 132ikl
# This software is license under the MIT license. It should be included in your copy of this software.
# A copy of the MIT license can be obtained at https://mit-license.org/

from flask import Flask, current_app, flash, g, jsonify, redirect, render_template, request, url_for
import bcrypt
import random
import sqlite3
import time
import urllib
import yaml

app = Flask(__name__)


def load_config():
    new_config = yaml.load(open('config.yml'))
    new_config = {k.lower(): v for k, v in new_config.items()}  # Make config keys case insensitive

    req_options = {'admin_username': 'admin', 'database_name': "urls", 'random_length': 4,
                   'allowed_chars': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_',
                   'random_gen_timeout': 5, 'site_name': 'liteshort', 'site_domain': None, 'show_github_link': True,
                   'secret_key': None, 'disable_api': False, 'subdomain': ''
                   }

    config_types = {'admin_username': str, 'database_name': str, 'random_length': int,
                    'allowed_chars': str, 'random_gen_timeout': int, 'site_name': str,
                    'site_domain': (str, type(None)), 'show_github_link': bool, 'secret_key': str,
                    'disable_api': bool, 'subdomain': (str, type(None))
                    }

    for option in req_options.keys():
        if option not in new_config.keys():  # Make sure everything in req_options is set in config
            new_config[option] = req_options[option]

    for option in new_config.keys():
        if option in config_types:
            matches = False
            if type(config_types[option]) is not tuple:
                config_types[option] = (config_types[option],)  # Automatically creates tuple for non-tuple types
            for req_type in config_types[option]:  # Iterates through tuple to allow multiple types for config options
                if type(new_config[option]) is req_type:
                    matches = True
            if not matches:
                raise TypeError(option + " is incorrect type")
    if not new_config['disable_api']:
        if 'admin_hashed_password' in new_config.keys() and new_config['admin_hashed_password']:
            new_config['password_hashed'] = True
        elif 'admin_password' in new_config.keys() and new_config['admin_password']:
            new_config['password_hashed'] = False
        else:
            raise TypeError('admin_password or admin_hashed_password must be set in config.yml')
    return new_config


def authenticate(username, password):
    return username == current_app.config['admin_username'] and check_password(password, current_app.config)


def check_long_exist(long):
    query = query_db('SELECT short FROM urls WHERE long = ?', (long,))
    for i in query:
        if i and (len(i['short']) <= current_app.config["random_length"]):  # Checks if query if pre-existing URL is same as random length URL
            return i['short']
    return False


def check_short_exist(short):  # Allow to also check against a long link
    if get_long(short):
        return True
    return False


def check_password(password, pass_config):
    if pass_config['password_hashed']:
        return bcrypt.checkpw(password.encode('utf-8'), pass_config['admin_hashed_password'].encode('utf-8'))
    elif not pass_config['password_hashed']:
        return password == pass_config['admin_password']
    else:
        raise RuntimeError('This should never occur! Bailing...')


def delete_url(deletion):
    result = query_db('SELECT * FROM urls WHERE short = ?', (deletion,), False, None)  # Return as tuple instead of row
    get_db().cursor().execute('DELETE FROM urls WHERE short = ?', (deletion,))
    get_db().commit()
    return len(result)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def generate_short(rq):
    timeout = time.time() + current_app.config['random_gen_timeout']
    while True:
        if time.time() >= timeout:
            return response(rq, None, 'Timeout while generating random short URL')
        short = ''.join(random.choice(current_app.config['allowed_chars'])
                        for i in range(current_app.config['random_length']))
        if not check_short_exist(short):
            return short


def get_long(short):
    row = query_db('SELECT long FROM urls WHERE short = ?', (short,), True)
    if row and row['long']:
        return row['long']
    return None


def list_shortlinks():
    result = query_db('SELECT * FROM urls', (), False, None)
    result = nested_list_to_dict(result)
    return result


def nested_list_to_dict(l):
    d = {}
    for nl in l:
            d[nl[0]] = nl[1]
    return d


def response(rq, result, error_msg="Error: Unknown error"):
    if rq.form.get('api') and not rq.form.get('format') == 'json':
        return "Format type HTML (default) not support for API"  # Future-proof for non-json return types
    if rq.form.get('format') == 'json':
        # If not result provided OR result doesn't exist, send error
        # Allows for setting an error message with explicitly checking in regular code
        if result:
            if result is True:  # Allows sending with no result (ie. during deletion)
                return jsonify(success=True)
            else:
                return jsonify(success=True, result=result)
        else:
            return jsonify(success=False, error=error_msg)
    else:
        if result and result is not True:
            flash(result, 'success')
            return render_template("main.html")
        elif not result:
            flash(error_msg, 'error')
            return render_template("main.html")
        return render_template("main.html")


def validate_short(short):
    for char in short:
        if char not in current_app.config['allowed_chars']:
            return response(request, None,
                            'Character ' + char + ' not allowed in short URL')
    return True


def validate_long(long):  # https://stackoverflow.com/a/36283503
    token = urllib.parse.urlparse(long)
    return all([token.scheme, token.netloc])

# Database connection functions


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            ''.join((current_app.config['database_name'], '.db')),
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.cursor().execute('CREATE TABLE IF NOT EXISTS urls (long,short)')
    return g.db


def query_db(query, args=(), one=False, row_factory=sqlite3.Row):
    get_db().row_factory = row_factory
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


app.config.update(load_config())  # Add YAML config to Flask config
app.secret_key = app.config['secret_key']
app.config['SERVER_NAME'] = app.config['site_domain']


@app.route('/', subdomain=app.config['subdomain'])
def main():
    return response(request, True)


@app.route('/<url>')
def main_redir(url):
    long = get_long(url)
    if long:
        return redirect(long, 301)
    flash('Short URL "' + url + '" doesn\'t exist', 'error')
    redirect_site = url_for('main')
    return redirect(redirect_site)


@app.route('/', methods=['POST'], subdomain=app.config['subdomain'])
def main_post():
    if request.form.get('long'):
        if not validate_long(request.form['long']):
            return response(request, None, "Long URL is not valid")
        if request.form.get('short'):
            # Validate long as URL and short custom text against allowed characters
            result = validate_short(request.form['short'])
            if validate_short(request.form['short']) is True:
                short = request.form['short']
            else:
                return result
            if get_long(short) == request.form['long']:
                return response(request, (('https://' + app.config['site_domain'] + '/') or request.base_url) + short,
                                'Error: Failed to return pre-existing non-random shortlink')
        else:
            short = generate_short(request)
        if check_short_exist(short):
            return response(request, None,
                            'Short URL already taken')
        long_exists = check_long_exist(request.form['long'])
        if long_exists and not request.form.get('short'):
            # TODO: un-hack-ify adding the protocol here
            return response(request, (('https://' + app.config['site_domain'] + '/') or request.base_url) + long_exists,
                            'Error: Failed to return pre-existing random shortlink')
        get_db().cursor().execute('INSERT INTO urls (long,short) VALUES (?,?)', (request.form['long'], short))
        get_db().commit()
        return response(request, (('https://' + app.config['site_domain'] + '/') or request.base_url) + short,
                        'Error: Failed to generate')
    elif request.form.get('api'):
        if current_app.config['disable_api']:
            return response(request, None, "API is disabled.")
        # All API calls require authentication
        if not request.authorization \
                or not authenticate(request.authorization['username'], request.authorization['password']):
            return response(request, None, "BaiscAuth failed")
        command = request.form['api']
        if command == 'list' or command == 'listshort':
            return response(request, list_shortlinks(), "Failed to list items")
        elif command == 'listlong':
            shortlinks = list_shortlinks()
            shortlinks = {v: k for k, v in shortlinks.items()}
            return response(request, shortlinks, "Failed to list items")
        elif command == 'delete':
            deleted = 0
            if 'long' not in request.form and 'short' not in request.form:
                return response(request, None, "Provide short or long in POST data")
            if 'short' in request.form:
                deleted = delete_url(request.form['short']) + deleted
            if 'long' in request.form:
                deleted = delete_url(request.form['long']) + deleted
            if deleted > 0:
                return response(request, "Deleted " + str(deleted) + " URLs")
            else:
                return response(request, None, "Failed to delete URL")
        else:
            return response(request, None, 'Command ' + command + ' not found')
    else:
        return response(request, None, 'Long URL required')


if __name__ == '__main__':
    app.run()
