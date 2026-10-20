#!/usr/bin/env bash
# Re-verifies the cities that are not OK in the results of check_aladhan_cities.sh.
#
# Usage: scripts/reverify_aladhan_cities.sh [results_file]
#
# The failing cities are retried in PASSES separate passes, spaced PASS_PAUSE seconds apart, so a
# temporary outage can be told apart from a city the API really cannot resolve. Each pass starts
# with a control request (Rabat): if it fails, the network/API is down, the pass is skipped and
# nothing is concluded about the cities.
#
# Final statuses written back to the results file:
#   OK            worked in at least one pass
#   UNSUPPORTED   failed in every valid pass, with the API answer (HTTP code + message)
#   TEMP_FAIL     not conclusive (control request failed, or not enough valid passes)
#
# Env: PASSES (default 3), PASS_PAUSE (seconds between passes, default 60),
#      DELAY (seconds between requests, default 1.1), RESOLVE_IP (see check_aladhan_cities.sh)

set -u

RESULTS="${1:-/tmp/aladhan_cities.tsv}"
PASSES="${PASSES:-3}"
PASS_PAUSE="${PASS_PAUSE:-60}"
DELAY="${DELAY:-1.1}"
TAB=$'\t'
API="https://api.aladhan.com/v1/timingsByCity/$(date +%d-%m-%Y)"
RESOLVE=()
[ -n "${RESOLVE_IP:-}" ] && RESOLVE=(--resolve "api.aladhan.com:443:${RESOLVE_IP}")

[ -f "$RESULTS" ] || { echo "No results file: $RESULTS (run check_aladhan_cities.sh first)"; exit 1; }

# query <city>: prints "<http_code>|<dhuhr or api message>"
query() {
  local body code info
  body=$(mktemp)
  code=$(curl -s -m 20 "${RESOLVE[@]+"${RESOLVE[@]}"}" -o "$body" -w '%{http_code}' -G "$API" \
    --data-urlencode "city=$1" --data-urlencode "country=MA" --data-urlencode "method=21")
  if [ "$code" = "200" ]; then
    info=$(grep -o '"Dhuhr":"[^"]*"' "$body" | head -1 | cut -d'"' -f4)
  else
    info=$(tr -d '\n' < "$body" | cut -c1-120)
  fi
  rm -f "$body"
  echo "${code}|${info}"
}

# update_result <id> <city> <status> <info>: keeps one line per city in the results file
update_result() {
  grep -v "^${1}${TAB}" "$RESULTS" > "$RESULTS.tmp"; mv "$RESULTS.tmp" "$RESULTS"
  printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >> "$RESULTS"
}

pending=$(awk -F'\t' '$3!="OK"{print $1"\t"$2}' "$RESULTS" | sort -n)
[ -z "$pending" ] && { echo "Nothing to re-verify."; exit 0; }

valid_passes=0
declare -a last_answer
for pass in $(seq 1 "$PASSES"); do
  control=$(query "Rabat")
  if [ "${control%%|*}" != "200" ]; then
    echo "[pass $pass/$PASSES] control request (Rabat) failed: $control -> pass skipped"
  else
    valid_passes=$((valid_passes + 1))
    echo "[pass $pass/$PASSES] control OK, testing $(printf '%s\n' "$pending" | wc -l | tr -d ' ') cities"
    still_failing=""
    while IFS="$TAB" read -r id city; do
      answer=$(query "$city")
      if [ "${answer%%|*}" = "200" ]; then
        update_result "$id" "$city" "OK" "${answer#*|}"
        echo "  $id $city => OK ${answer#*|}"
      else
        last_answer[$id]="$answer"
        still_failing+="${id}${TAB}${city}"$'\n'
        echo "  $id $city => FAIL $answer"
      fi
      sleep "$DELAY"
    done <<< "$pending"
    pending=$(printf '%s' "$still_failing" | sed '/^$/d')
    [ -z "$pending" ] && break
  fi
  [ "$pass" -lt "$PASSES" ] && sleep "$PASS_PAUSE"
done

while IFS="$TAB" read -r id city; do
  [ -z "$id" ] && continue
  if [ "$valid_passes" -ge 2 ]; then
    update_result "$id" "$city" "UNSUPPORTED" "${last_answer[$id]:-unknown}"
  else
    update_result "$id" "$city" "TEMP_FAIL" "${last_answer[$id]:-no valid pass}"
  fi
done <<< "$pending"

echo
echo "===== SUMMARY ($RESULTS, valid passes: $valid_passes/$PASSES) ====="
for s in OK UNSUPPORTED TEMP_FAIL; do
  echo "$s: $(awk -F'\t' -v s="$s" '$3==s' "$RESULTS" | wc -l | tr -d ' ')"
done
echo
echo "--- UNSUPPORTED (id city api answer) ---"
awk -F'\t' '$3=="UNSUPPORTED"{print $1" "$2" | "$4}' "$RESULTS" | sort -n
echo "--- TEMP_FAIL ---"
awk -F'\t' '$3=="TEMP_FAIL"{print $1" "$2" | "$4}' "$RESULTS" | sort -n
