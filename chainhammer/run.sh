#!/usr/bin/env bash
set -euo pipefail

# ----------------------------
# Chainhammer (Docker-friendly)
# - Creates logs/
# - Doesn't require venv
# - Skips analytics by default (CH_ANALYZE=0)
# ----------------------------

# Defaults
DBFILE="temp.db"
INFOFILE="hammer/last-experiment.json"  # path relative to /opt/chainhammer
TPSLOG="logs/tps.py.log"
DEPLOYLOG="logs/deploy.py.log"
SENDLOG="logs/send.py.log"

# For better error messages
current_command=""
last_command=""
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
trap 'rc=$?; echo; echo "\"${last_command}\" command failed with exit code ${rc}."; exit ${rc}' ERR

title() {
  echo "============================="
  echo "= $1"
  echo "============================="
}

# CH_ANALYZE: 0 (default) => only deploy/send/tps load run
: "${CH_ANALYZE:=0}"

# Validate required env vars
if [[ -z "${CH_TXS:-}" || -z "${CH_THREADING:-}" ]]; then
  echo "You must set 2 ENV variables, examples:"
  echo "export CH_TXS=1000 CH_THREADING=sequential"
  echo "export CH_TXS=5000 CH_THREADING=\"threaded2 20\""
  exit 1
fi

# Argument: info word (we pass "quick" or "run")
if (( $# != 1 )); then
  echo "Syntax:"
  echo "./run.sh info-word"
  exit 1
fi

INFOWORD="$1"

# Ensure directories exist (fixes your tee/log failures)
mkdir -p logs hammer

echo
title "chainhammer - run all"
echo
echo "infoword: ${INFOWORD}"
echo "number of transactions: ${CH_TXS}"
echo "concurrency algo: ${CH_THREADING}"
echo
echo "infofile: ${INFOFILE}"
echo "blocks database: ${DBFILE}"
echo "log files:"
echo "${TPSLOG}"
echo "${DEPLOYLOG}"
echo "${SENDLOG}"
echo

title "activate virtualenv (optional)"
if [[ -f "env/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "env/bin/activate"
  echo "virtualenv activated: env/"
else
  echo "No env/ virtualenv found. Continuing with system Python (OK in Docker)."
fi
echo
python --version
echo

# Work inside hammer/ (original chainhammer flow)
cd hammer

# IMPORTANT: inside hammer/, INFOFILE should be just basename
INFOFILE_BASENAME="last-experiment.json"
rm -f "${INFOFILE_BASENAME}" || true

title "is_up.py"
echo "Loops until the node is answering on the expected port."
./is_up.py
echo "Great, node is available now."
echo

title "tps.py"
echo "Start listener tps.py, show here but also log into file ../${TPSLOG}"
echo "This ENDS after send.py below writes a new INFOFILE ${INFOFILE_BASENAME}"
unbuffer ./tps.py | tee "../${TPSLOG}" &
echo

title "sleep 1.5 seconds"
echo "To have tps.py say its thing before deploy.py starts printing"
echo
sleep 1.5
echo

title "deploy.py"
echo "Deploy the smartContract; deploy.py triggers tps.py to START counting."
echo "Logging into file ../${DEPLOYLOG}."
echo
./deploy.py > "../${DEPLOYLOG}"
echo

title "send.py"
echo "Send ${CH_TXS} transactions with concurrency algo '${CH_THREADING}'."
echo "Then send.py triggers tps.py to end counting. Logging into file ../${SENDLOG}."
echo
# shellcheck disable=SC2086
./send.py "${CH_TXS}" ${CH_THREADING} > "../${SENDLOG}"
echo

title "sleep 2"
echo "Wait 2 seconds until also tps.py has written its results."
echo
sleep 2
echo

cd ..

# If CH_ANALYZE=0, stop here (this is enough for load testing)
if [[ "${CH_ANALYZE}" != "1" ]]; then
  title "Done (load test complete)"
  echo "Skipped reader/diagram steps (CH_ANALYZE=0)."
  echo "Logs:"
  echo "  ${TPSLOG}"
  echo "  ${DEPLOYLOG}"
  echo "  ${SENDLOG}"
  echo "Infofile:"
  echo "  ${INFOFILE}"
  exit 0
fi

# Analytics path (optional) - requires extra deps like pandas/matplotlib
title "blocksDB_create.py"
echo "Read blocks from node into SQL db"
cd reader
./blocksDB_create.py "${DBFILE}" "../${INFOFILE}"
echo

title "blocksDB_diagramming.py"
echo "Make time series diagrams from SQL db"
./blocksDB_diagramming.py "${DBFILE}" "${INFOWORD}" "../${INFOFILE}"
echo

title "page_generator.py"
./page_generator.py "../${INFOFILE}" "../${TPSLOG}"
echo

cd ..

title "Ready."
echo "See the generated image(s) and the .md/.html pages."
echo