from getpass import getpass

import bcrypt


def hash_passwd():
    salt = bcrypt.gensalt()
    try:
        unhashed = getpass("Type password to hash: ")
        unhashed2 = getpass("Confirm: ")
    except (KeyboardInterrupt, EOFError):
        pass

    if unhashed != unhashed2:
        print("Passwords don't match.")
        return None

    hashed = bcrypt.hashpw(unhashed.encode("utf-8"), salt)

    print("Password hash: " + hashed.decode("utf-8"))
