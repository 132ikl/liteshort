from flask import Flask, request, current_app, g, render_template
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
                   'random_gen_timeout': 5, 'site_name': 'liteshort'
                   }

    config_types = {'admin_username': str, 'database_name': str, 'random_length': int,
                    'allowed_chars': str, 'random_gen_timeout': int, 'site_name': str}

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


def check_short_exist(short):
    query = query_db('SELECT long FROM urls WHERE short = ?', (short,))
    if query:
        return True
    return False


def check_long_exist(long):
    query = query_db('SELECT short FROM urls WHERE long = ?', (long,))
    for i in query:
        if i and (len(i['short']) <= current_app.config["random_length"]):  # Checks if query if pre-existing URL is same as random length URL
            return i['short']
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


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def response(rq, short, error_msg=None):
    if 'json' in rq.form and rq.form['json']:
        pass
    else:
        if short:
            return render_template("main.html", result=(True, rq.base_url + short))
        else:
            return render_template("main.html", result=(False, error_msg))


config = load_config()

app = Flask(__name__)
app.config.update(config)  # Add loaded YAML config to Flask config


@app.route('/')
def main():
    return render_template("main.html")


@app.route('/', methods=['POST'])
def main_post():
    if 'long' in request.form and request.form['long']:
        if 'short' in request.form and request.form['short']:
            for char in request.form['short']:
                if char not in current_app.config['allowed_chars']:
                    return response(request, None, 'Character ' + char + ' not allowed in short URL.')
            short = request.form['short']
        else:
            timeout = time.time() + current_app.config['random_gen_timeout']
            while True:
                if time.time() >= timeout:
                    return response(request, None, 'Timeout while generating random short URL.')
                short = generate_short()
                if not check_short_exist(short):
                    break
        short_exists = check_short_exist(short)
        long_exists = check_long_exist(request.form['long'])
        if long_exists and not ('short' in request.form and request.form['short']):
            return response(request, long_exists)
        if short_exists:
            return response(request, None, "Short URL already exists.")
        database = get_db()
        database.cursor().execute("INSERT INTO urls (long,short) VALUES (?,?)", (request.form['long'], short))
        database.commit()
        database.close()
        return response(request, short)
    else:
        return "Long URL required!"


if __name__ == '__main__':
    app.run()
