#!/bin/bash
set -eux

CONTNAME=lxdrunner-build
USER=app

if ! lxc info $CONTNAME >/dev/null ; then
  lxc launch images:alpine/3.14 $CONTNAME
  sleep 3
fi

lxc exec $CONTNAME -- sh <<-END
 set -eux
 apk update
 apk add python3 py3-pip py3-setuptools py3-cryptography
 id $USER || adduser -D $USER
END

MY_UID=$(lxc exec $CONTNAME -- id -u $USER )
VERSION=$(python3 setup.py --version)
WHEEL=$(basename dist/*.whl)

lxc file push dist/$WHEEL $CONTNAME/home/$USER/
lxc file push config.yml.example $CONTNAME/home/$USER/config.yml

lxc exec $CONTNAME --user $MY_UID --group $MY_UID -- sh <<-END
 cd ~$USER
 echo 'PATH=~/.local/bin/:$PATH' > ~$USER/.profile
 pip3 install ./$WHEEL
END

lxc file push service/lxdrunner.openrc $CONTNAME/etc/init.d/lxdrunner
lxc exec $CONTNAME -- sh <<-END
 rc-update add lxdrunner
END

