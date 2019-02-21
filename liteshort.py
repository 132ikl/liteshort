from flask import Flask
import yaml


def load_config():
    new_config = yaml.load(open("config.yml"))
    if "admin_hashed_password" in new_config.keys():
        new_config["password"] = new_config["admin_hashed_password"]
    elif "admin_password" in new_config.keys():
        new_config["password"] = new_config["admin_password"]
    else:
        raise Exception("admin_password or admin_hashed_password must be set in config.yml")
    return new_config


config = load_config()
print(config["password"])

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run()
