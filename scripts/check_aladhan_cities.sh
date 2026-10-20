#!/usr/bin/env bash
# Checks which cities of the bundled list are supported by the Aladhan API.
#
# Usage: scripts/check_aladhan_cities.sh [results_file]
#
# Results are stored in a TSV file (id, city, status, dhuhr) and the script is
# resumable: cities already marked OK are skipped, the others are retried.
# Re-run it until the summary shows no more TEMP_FAIL.
#
# Statuses: OK, NOT_FOUND (API answered 4xx), TEMP_FAIL (5xx / network, may work later)
#
# Env: DELAY (seconds between requests, default 1.1), RETRIES (attempts per city, default 1)
#      RESOLVE_IP (optional): bypass the system DNS and connect to this IP, for networks whose
#      DNS sometimes answers a sinkhole address for api.aladhan.com (curl then ends with HTTP 000).
#      Get the real IP with: dig +short api.aladhan.com (the one that is not a sinkhole)

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CITIES_YML="$ROOT/moroccan_prayer_times/translations/en.yml"
RESULTS="${1:-/tmp/aladhan_cities.tsv}"
DELAY="${DELAY:-1.1}"
RETRIES="${RETRIES:-1}"
API="https://api.aladhan.com/v1/timingsByCity/$(date +%d-%m-%Y)"
RESOLVE=()
[ -n "${RESOLVE_IP:-}" ] && RESOLVE=(--resolve "api.aladhan.com:443:${RESOLVE_IP}")
TAB=$'\t'

touch "$RESULTS"

# Lines of the "cities:" section of en.yml look like:    _99: 'Meknes'
cities=$(awk '/^  cities:/{f=1;next} f&&/^    _[0-9]+:/{print} f&&/^  [a-z]/{f=0}' "$CITIES_YML" \
  | sed -E "s/^    _([0-9]+): *['\"]?([^'\"]*)['\"]?.*/\1${TAB}\2/")

total=$(printf '%s\n' "$cities" | wc -l | tr -d ' ')
n=0

while IFS="$TAB" read -r id city; do
  n=$((n + 1))
  if grep -qE "^${id}${TAB}.*${TAB}OK${TAB}" "$RESULTS"; then
    continue
  fi

  status="TEMP_FAIL"; dhuhr="-"
  for attempt in $(seq 1 "$RETRIES"); do
    body=$(mktemp)
    code=$(curl -s -m 20 "${RESOLVE[@]+"${RESOLVE[@]}"}" -o "$body" -w '%{http_code}' -G "$API" \
      --data-urlencode "city=$city" --data-urlencode "country=MA" --data-urlencode "method=21")
    if [ "$code" = "200" ]; then
      dhuhr=$(grep -o '"Dhuhr":"[^"]*"' "$body" | head -1 | cut -d'"' -f4)
      status="OK"; rm -f "$body"; break
    elif [[ "$code" =~ ^4 ]]; then
      status="NOT_FOUND"; rm -f "$body"; break
    fi
    rm -f "$body"
    sleep "$(awk -v d="$DELAY" -v a="$attempt" 'BEGIN{print d * a * 2}')"
  done

  # Keep only the latest line of each city
  grep -v "^${id}${TAB}" "$RESULTS" > "$RESULTS.tmp"; mv "$RESULTS.tmp" "$RESULTS"
  printf '%s\t%s\t%s\t%s\n' "$id" "$city" "$status" "$dhuhr" >> "$RESULTS"
  echo "[$n/$total] $id $city => $status $dhuhr"
  sleep "$DELAY"
done <<< "$cities"

echo
echo "===== SUMMARY ($RESULTS) ====="
for s in OK NOT_FOUND TEMP_FAIL; do
  echo "$s: $(awk -F'\t' -v s="$s" '$3==s' "$RESULTS" | wc -l | tr -d ' ')"
done
echo
echo "--- NOT_FOUND ---"
awk -F'\t' '$3=="NOT_FOUND"{print $1" "$2}' "$RESULTS" | sort -n
echo "--- TEMP_FAIL (re-run the script) ---"
awk -F'\t' '$3=="TEMP_FAIL"{print $1" "$2}' "$RESULTS" | sort -n
