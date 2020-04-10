import logging
from pathlib import Path
from shutil import copyfile

from appdirs import site_config_dir, user_config_dir
from pkg_resources import resource_filename
from yaml import safe_load

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


def get_config():
    APP = "liteshort"
    AUTHOR = "132ikl"

    paths = [
        Path("/etc/liteshort"),
        Path(site_config_dir(APP, AUTHOR)),
        Path(user_config_dir(APP, AUTHOR)),
        Path(),
    ]

    for path in paths:
        f = path / "config.yml"
        if f.exists():
            LOGGER.debug(f"Selecting config file {f}")
            return open(f, "r")

    for path in paths:
        try:
            path.mkdir(exist_ok=True)
            template = resource_filename(__name__, "config.template.yml")
            copyfile(template, (path / "config.template.yml"))
            copyfile(template, (path / "config.yml"))
            return open(path / "config.yml", "r")
        except (PermissionError, OSError) as e:
            LOGGER.warn(f"Failed to create config in {path}")
            LOGGER.debug("", exc_info=True)

    raise FileNotFoundError("Cannot find config.yml, and failed to create it")


# TODO: yikes
def load_config():
    with get_config() as config:
        configYaml = safe_load(config)
    config = {
        k.lower(): v for k, v in configYaml.items()
    }  # Make config keys case insensitive

    req_options = {
        "admin_username": "admin",
        "database_name": "urls",
        "random_length": 4,
        "allowed_chars": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_",
        "random_gen_timeout": 5,
        "site_name": "liteshort",
        "site_domain": None,
        "show_github_link": True,
        "secret_key": None,
        "disable_api": False,
        "subdomain": "",
        "latest": "l",
        "selflinks": False,
        "blocklist": [],
    }

    config_types = {
        "admin_username": str,
        "database_name": str,
        "random_length": int,
        "allowed_chars": str,
        "random_gen_timeout": int,
        "site_name": str,
        "site_domain": (str, type(None)),
        "show_github_link": bool,
        "secret_key": str,
        "disable_api": bool,
        "subdomain": (str, type(None)),
        "latest": (str, type(None)),
        "selflinks": bool,
        "blocklist": list,
    }

    for option in req_options.keys():
        if (
            option not in config.keys()
        ):  # Make sure everything in req_options is set in config
            config[option] = req_options[option]

    for option in config.keys():
        if option in config_types:
            matches = False
            if type(config_types[option]) is not tuple:
                config_types[option] = (
                    config_types[option],
                )  # Automatically creates tuple for non-tuple types
            for req_type in config_types[
                option
            ]:  # Iterates through tuple to allow multiple types for config options
                if type(config[option]) is req_type:
                    matches = True
            if not matches:
                raise TypeError(option + " is incorrect type")
    if not config["disable_api"]:
        if "admin_hashed_password" in config.keys() and config["admin_hashed_password"]:
            config["password_hashed"] = True
        elif "admin_password" in config.keys() and config["admin_password"]:
            config["password_hashed"] = False
        else:
            raise TypeError(
                "admin_password or admin_hashed_password must be set in config.yml"
            )
    return config
