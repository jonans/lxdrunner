#!/bin/bash -x

set -e
exec 2>&1

PKGDIR="/opt/runner"
PKGNAME=actions-runner.tgz
PKGFILE="$PKGDIR/$PKGNAME"
SETUPFILE="$PKGDIR/setupvars.conf"

RUNNERUSER=runner
RUNNERHOME="/home/$RUNNERUSER"

CHECK_ARGS="GHA_TOKEN GHA_URL GHA_NAME"

fail() {
    printf "$1"
    exit 1
}

[ -f $SETUPFILE ] && source $SETUPFILE

# Ensure required vars are set

for var in $CHECK_ARGS ; do
    eval val=\$$var
    if [ -z "$val" ] ; then
        ERRS="${ERRS}${var} is not set\n"
    fi
done

[ -n "$ERRS" ] && fail "$ERRS"

# User handling

setup_user(){

    # Avoid adduser race condition with cloud-init. Wait till done.
    which cloud-init && cloud-init status -w

    adduser runner --disabled-password --gecos ""
    [ "$?" -eq "0" ] || fail "Add user failed"
    adduser runner sudo
    [ "$?" -eq "0" ] || fail "Add group failed"
}

# Package handling

unpack(){
    [ -d "$RUNNERHOME" ] || fail "Home $RUNNERHOME doesnt exist"
    [ -f "$PKGFILE" ] || fail "Package $PKGFILE doesnt exist"

    sudo -u $RUNNERUSER tar -xvf $PKGFILE  -C $RUNNERHOME >/dev/null || fail "Unpack failed"
}

delaypoweroff(){
    sleep 5
    poweroff -f
}

background(){
  local cmd=$@
  set +e
  echo "Backgrounding: $*"
  # Redirect FD's
  $cmd </dev/null &>/dev/null & disown
}

start_runner(){
  sudo -u $RUNNERUSER ./run.sh --once
  sudo -u $RUNNERUSER ./config.sh remove --unattended --token "$GHA_TOKEN"
  delaypoweroff
}

reg_runner(){
  sudo -u $RUNNERUSER ./config.sh --unattended --url "$GHA_URL" --token "$GHA_TOKEN" \
     --replace --name "$GHA_NAME" --labels "$GHA_EXTRA_LABELS"
}

begin_runner(){
    cd $RUNNERHOME

    if reg_runner ; then
        echo "Runner registered. Starting up."
        background start_runner
    else
        echo "Error registering runner"
        exit 1
    fi
}


setup_user
unpack
begin_runner

exit
