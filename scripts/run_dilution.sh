#!/bin/bash
# Run one account's share of the second study (DILUTION.md), one call at a time.
#
#   scripts/run_dilution.sh KEY_ENV SUFFIX "TEMPLATES" "MALT_FAMILIES"
#
# The gateway allows one call at a time per account, so the work is split across two accounts by
# template. Each account writes its own results files (the second account's end in SUFFIX), and
# the files are joined before dilution_report.py reads them. Each stage is run twice: the second
# pass reads again any call that was cut off mid-way.
set -u
KEY_ENV="$1"; SFX="$2"; TEMPLATES="$3"; MALT="$4"
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-${TMPDIR:-/tmp}/uv-cache}"

DIL=""
for t in $TEMPLATES; do for c in k01 k03 k07 k15 pad; do DIL="$DIL dil-$t-$c"; done; done

stage() {  # name model set arm readings budget families...
  local name="$1" model="$2" set="$3" arm="$4" readings="$5" budget="$6"; shift 6
  local out="results/raw/${name}-${model}${SFX}.jsonl" log="results/${name}-${model}${SFX}.log"
  for retry in "" "--retry-maybe-billed"; do
    uv run --offline python monitor.py --set "$set" --conditions raw --instructions "$arm" --families "$@" \
      --models "$model" --readings "$readings" --out "$out" --api-key-env "$KEY_ENV" --workers 1 \
      --max-credits "$budget" $retry --run >> "$log" 2>&1
  done
  echo "$(date '+%H:%M') finished $name $model$SFX: $(tail -1 "$log" | cut -c1-150)"
}

stage dilution         deepseek-v4-flash dilution score   20 12 $DIL
stage dilution-verdict deepseek-v4-flash dilution verdict 20 12 $DIL
stage dilution         gemma-4-31b-it    dilution score   20 6  $DIL
stage dilution-verdict gemma-4-31b-it    dilution verdict 20 6  $DIL
stage verdict-malt     deepseek-v4-flash malt     verdict 20 12 $MALT
stage verdict-malt     gemma-4-31b-it    malt     verdict 20 6  $MALT
stage dilution         qwen3.5-397b      dilution score   10 40 $DIL
