#!/usr/bin/env bash
# usage: scripts/summarize.sh <scenario.yaml> <name>   (runs, grades, prints one line)
cd "$(dirname "$0")/.."
scripts/run_scenario.sh "$1" "$2" >/dev/null 2>&1
printf "%-12s " "$2"
sed -n 9,10p reports/$2.md | tail -1 | cut -d'|' -f2-5 | tr -d '\n'
grep "applied —" reports/$2.md | tr -d '\n'
echo " errs=$(grep -c ERROR logs/ctl_$2.log) alerts=$(sqlite3 state/$2.db 'select count(*) from alerts')"
