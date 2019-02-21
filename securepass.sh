#!/bin/sh

## bcrypt passwd generator ##
#############################
CMD=$(which htpasswd 2>/dev/null)
OPTS="-nBC 15"

read -p "Username: " USERNAME

check_config() {
    if [ -z $CMD ]; then
        printf "Exiting: htpasswd is missing.\n"
        exit 1
    fi

    if [ -z "$USERNAME" ]; then
            usage
    fi
}

check_config $USERNAME
printf "Generating Bcrypt hash for username: $USERNAME\n\n"
$CMD $OPTS $USERNAME
exit $?
