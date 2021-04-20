#!/bin/bash -x

exec 2>&1


PKGDIR="/opt/runner"
PKGNAME=actions-runner.tgz
PKGFILE="$PKGDIR/$PKGNAME"

RUNNERUSER=runner
RUNNERHOME="/home/$RUNNERUSER"

CHECK_ARGS="GHA_TOKEN GHA_URL GHA_NAME"

function fail(){
    printf "$1"
    exit 1
}

cd "$PKGDIR" || fail "Cant cd to $PKGDIR"

# Ensure required vars are set
for var in $CHECK_ARGS ; do
    if [ -z "${!var}" ] ; then
        ERRS="${ERRS}${var} is not set\n"
    fi
done

export > vars.sh

[ -n "$ERRS" ] && fail "$ERRS"

#Create runner user

adduser runner --disabled-password --gecos ""
[ $? == 0 ] || fail "Add user failed"
adduser runner sudo
[ $? == 0 ] || fail "Add group failed"

[ -d "$RUNNERHOME" ] || fail "Home directory doesnt exist"


printf "$PWD"

tar -xvf $PKGFILE  -C $RUNNERHOME >/dev/null

chown $RUNNERUSER.$RUNNERUSER -R $RUNNERHOME

cd $RUNNERHOME

function delaypoweroff(){
    sleep 5
    poweroff -f
}

function startrunner(){
  sudo -u $RUNNERUSER ./run.sh --once
  sudo -u $RUNNERUSER ./config.sh remove --unattended --token "$GHA_TOKEN"
  delaypoweroff
}

function reg_runner(){
  sudo -u $RUNNERUSER ./config.sh --unattended --url "$GHA_URL" --token "$GHA_TOKEN" \
     --replace --name "$GHA_NAME" --labels "$GHA_EXTRA_LABELS"
}

function background(){
  local cmd=$@
  echo "Backgrounding: $cmd"
  # Redirect FD's
  $cmd </dev/null &>>setuprunner.log & disown
}

if reg_runner ; then
    echo "Runner registered. Starting up."
    background startrunner
else
    echo "Error registering runner"
    background delaypoweroff
    exit 1
fi

exit
