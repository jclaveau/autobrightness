DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
setsid bash $DIR/run.sh >/dev/null 2>&1 < /dev/null &
