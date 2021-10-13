#!/bin/bash
set -eux

CONTNAME=lxdrunner-build
USER=app

if ! lxc info $CONTNAME >/dev/null ; then
  lxc launch ubuntu:focal $CONTNAME
  sleep 3
fi

lxc exec $CONTNAME -- sh <<-END
 set -eux
 apt update
 apt install -y python3-dev python3-pip
 id $USER || adduser --disabled-password --gecos "" $USER
 loginctl enable-linger $USER
END

MY_UID=$(lxc exec $CONTNAME -- id -u $USER )

tar -c ../lxdrunner | lxc exec $CONTNAME --user $MY_UID --group $MY_UID -- tar -xv -C /home/app

lxc exec $CONTNAME --user $MY_UID --group $MY_UID -- sh <<-END
 cd ~$USER/lxdrunner
 make pip-install
 make install-user-unit
END

