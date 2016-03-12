#!/bin/sh

basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"

export MICROPYPATH="$basedir/libs/tiny_datetime:$MICROPYPATH"
export MICROPYPATH="$basedir/libs/tiny_distutils:$MICROPYPATH"
export MICROPYPATH="$basedir/pylibs/csv:$MICROPYPATH"
export MICROPYPATH="$basedir/pylibs/configparser:$MICROPYPATH"
export MICROPYPATH="/home/mb/develop/git/micropython-lib/build/:$MICROPYPATH"

exec /home/mb/develop/git/micropython/unix/micropython -X heapsize=134217728 "$@"
