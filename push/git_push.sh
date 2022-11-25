SCRIPTDIR=$(dirname "$0")
BASEDIR=$(cd "$SCRIPTDIR" && pwd)
HOMEDIR=${BASEDIR}/..
GIT_DIR=$(cd "${HOMEDIR}" && pwd)
git add .
git commit -m "$1"
git push origin "$2"