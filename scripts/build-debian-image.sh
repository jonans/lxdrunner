#!/bin/bash
set -eux

CONTNAME=lxdrunner-build
USER=app

if ! lxc info $CONTNAME >/dev/null ; then
  lxc launch images:debian/11 $CONTNAME
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
VERSION=$(python3 setup.py --version)
WHEEL=lxdrunner-$VERSION-py3-none-any.whl

lxc file push dist/$WHEEL $CONTNAME/home/$USER/

lxc exec $CONTNAME --user $MY_UID --group $MY_UID -- sh <<-END
 cd ~$USER
 pip install ./$WHEEL
END

