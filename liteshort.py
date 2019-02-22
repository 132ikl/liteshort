from flask import Flask, Response, request, current_app, g, send_from_directory
import bcrypt
import random
import sqlite3
import time
import yaml


def load_config():
    new_config = yaml.load(open('config.yml'))
    new_config = {k.lower(): v for k, v in new_config.items()}  # Make config keys case insensitive

    req_options = {'admin_username': 'admin', 'database_name': "urls", 'random_length': 4,
                   'allowed_chars': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_',
                   'random_gen_timeout': 5
                   }

    config_types = {'admin_username': str, 'database_name': str, 'random_length': int,
                    'allowed_chars': str, 'random_gen_timeout': int}

    for option in req_options.keys():
        if option not in new_config.keys():  # Make sure everything in req_options is set in config
            new_config[option] = req_options[option]

    for option in new_config.keys():
        if option in config_types:
            if not type(new_config[option]) is config_types[option]:
                raise TypeError(option + " must be type " + config_types[option].__name__)

    if 'admin_hashed_password' in new_config.keys():  # Sets config value to see if bcrypt is required to check password
        new_config['password_hashed'] = True
    elif 'admin_password' in new_config.keys():
        new_config['password_hashed'] = False
    else:
        raise TypeError('admin_password or admin_hashed_password must be set in config.yml')
    return new_config


def check_password(password, pass_config):
    if pass_config['password_hashed']:
        return bcrypt.checkpw(password.encode('utf-8'), pass_config['admin_hashed_password'].encode('utf-8'))
    elif not pass_config['password_hashed']:
        return password == pass_config['admin_password']
    else:
        raise RuntimeError('This should never occur! Bailing...')


def check_short_exist(database, short):
    database.cursor().execute("SELECT long FROM urls WHERE short = ?", (short,))
    result = database.cursor().fetchone()
    if database.cursor().fetchone():
        return result
    return False


def check_long_exist(database, long):
    database.cursor().execute("SELECT short FROM urls WHERE long = ?", (long,))
    result = database.cursor().fetchone()
    if database.cursor().fetchone():
        return result
    return False


def generate_short():
    return ''.join(random.choice(current_app.config['allowed_chars'])
                   for i in range(current_app.config['random_length']))


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            ''.join((current_app.config['database_name'], '.db')),
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.cursor().execute('CREATE TABLE IF NOT EXISTS urls (long,short)')
    return g.db


config = load_config()

app = Flask(__name__)
app.config.update(config)  # Add loaded YAML config to Flask config


@app.route('/')
def main():
    return send_from_directory('static', 'main.html')


@app.route('/', methods=['POST'])
def main_post():
    if 'long' in request.form and request.form['long']:
        database = get_db()
        if 'short' in request.form and request.form['short']:
            for char in request.form['short']:
                if char not in current_app.config['allowed_chars']:
                    return Response('Character ' + char + ' not allowed in short URL.', status=200)
            short = request.form['short']
        else:
            timeout = time.time() + current_app.config['random_gen_timeout']
            while True:
                if time.time() >= timeout:
                    return Response('Timeout while generating random short URL.', status=200)
                short = generate_short()
                if not check_short_exist(database, short):
                    break
        short_exists = check_short_exist(database, short)
        long_exists = check_long_exist(database, request.form['long'])
        if long_exists and 'short' not in request.form:
            return request.base_url + long_exists
        if short_exists:
            return Response('Short URL already exists.', status=200)
        database.cursor().execute("INSERT INTO urls (long,short) VALUES (?,?)", (request.form['long'], short))
        database.commit()
        database.close()
        return "Your shortened URL is available at " + request.base_url + short
    else:
        return "Long URL required!"


if __name__ == '__main__':
    app.run()
