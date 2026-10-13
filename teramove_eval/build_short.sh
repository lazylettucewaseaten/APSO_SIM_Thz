#!/bin/sh
# Compile TeraHertz-short/paper.tex with tectonic, retrying flaky bundle downloads.
cd "$(dirname "$0")/../TeraHertz-short" || exit 1
for i in $(seq 1 30); do
  timeout 600 tectonic --keep-logs paper.tex > tec.log 2>&1 && { echo "compiled (try $i)"; exit 0; }
  sleep 2
done
grep -e '^error' tec.log | head -3
exit 1
