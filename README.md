# liteshort
liteshort is a link shortener designed with lightweightness, user and sysadmin-friendliness, privacy, and configurability in mind.

*Why liteshort over other URL shorteners?*
liteshort is designed with the main goal of being lightweight. It does away with all the frills of other link shorteners and allows the best of the basics at a small resource price. liteshort uses under 20 MB of memory idle, per worker. liteshort has an easy-to-use API and web interface. liteshort doesn't store any more information than necessary: just the long and short URLs. It does not log the date of creation, the remote IP, or any other information.

liteshort uses Python 3, [Flask](http://flask.pocoo.org/), SQLite3, and [uwsgi](https://uwsgi-docs.readthedocs.io/en/latest/) for the backend. 
The frontend is a basic POST form using [PureCSS](https://purecss.io).

![liteshort screenshot](https://fs.ikl.sh/selif/4cgndb6e.png)

## Installation
This installation procedure assumes that you plan to installing using a web server reverse proxy through a unix socket. This guide is loosely based upon DigitalOcean's [Flask/uWSGI/nginx guide](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uswgi-and-nginx-on-ubuntu-18-04).
Before installing, you must the following or your distribution's equivalent must be installed:
* python3-pip 
* python3-dev 
* python3-setuptools
* python3-venv
* build-essential

Start in the directory you wish to install to and modify to fit your installation. It is recommended to use a user specifically for liteshort and the www-data group for your installation folder.

```sh
git clone https://github.com/132ikl/liteshort
python3 -m venv virtualenv
source virtualenv/bin/activate
pip install wheel
pip install bcrypt flask pyyaml uwsgi
```

Edit `liteshort.ini` and `liteshort.service` as seen fit. Then edit `config.yml` according to the [Configuration](#configuration) section.

Finally,
```sh
cp liteshort.service /etc/systemd/system/
systemctl enable liteshort
systemctl start liteshort
```

liteshort is now accessible through a reverse proxy. The socket file is created in the install path.

## Configuration
The configuration file has an explanation for each option. This section will detail the mandatory options to be set before the program is able to be started.

`admin_hashed_password` or `admin_password`
* These must be set in order to use the API. If you do not care about the API, simply set `disable_api` to true.
As to not store the API password in cleartext, `admin_hashed_password` is preferred over `admin_password`. Run `securepass.sh` in order to generate the password hash. Set `admin_hashed_password` to the output of the script, excluding the username header at the beginning of the hash.
Note that using admin_hashed_password is more resource-intensive than `admin_password`, so the API will be noticeably slower when using `admin_hashed_password`.

`secret_key`
* This is used for cookies in order to store messages between requests. It should be a randomized key 12-16 characters, comprised of letters, number, and symbols. A standard password from a generator works fine.


## API
All API requests should have the POST form data `format` set to `json`.
In order to create a new short URL, simply make a POST request with the form data `long` set to your long link and, optionally, set `short` to your short link.
Everything other than creation of links requires BasicAuth using the username and password defined in the configuration file. To use the following commands, set `api` to the command in the form data of your request.
* `list` and `listshort`
    * Lists all links the the database, sorted by short links.
* `listlong`
    * Lists all links in the database, sorted by long links.
* `delete`
    * Deletes a URL. In the form data, set `short` to the short link you want to delete, or set `long` to delete all short links that redirect to the provided long link.
