#!/bin/bash
# Run one account's share of the third study (RELATED.md), then the rest of the second study.
#
#   scripts/run_related.sh KEY_ENV SUFFIX "TEMPLATES" "MALT_FAMILIES"
#
# The gateway allows one call at a time per account, so the work is split across two accounts by
# template. Each account writes its own results files (the second account's end in SUFFIX), and
# the files are joined before related_report.py and dilution_report.py read them. Each stage is
# run twice: the second pass reads again any call that was cut off mid-way.
#
# The order is the one RELATED.md fixes: the confirmatory reviewer's score readings, its
# two-number readings, the replication reviewer, the rest of the second study, then the verdict
# readings on this set. The second study's qwen3.5-397b replication is dropped, as RELATED.md says.
set -u
KEY_ENV="$1"; SFX="$2"; TEMPLATES="$3"; MALT="$4"
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-${TMPDIR:-/tmp}/uv-cache}"

REL=""; TWO=""; R7=""; K07=""; DIL=""
for t in $TEMPLATES; do
  for c in r1 r3 r7 look imp0 imp7; do REL="$REL rel-$t-$c"; done
  TWO="$TWO rel-$t-r7 rel-$t-look"; R7="$R7 rel-$t-r7"; K07="$K07 dil-$t-k07"
  for c in k01 k03 k07 k15 pad; do DIL="$DIL dil-$t-$c"; done
done

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

stage related          deepseek-v4-flash related  score   20 12 $REL
stage related-two      deepseek-v4-flash related  two     20 12 $TWO
stage dilution-two     deepseek-v4-flash dilution two     20 12 $K07
stage related          gemma-4-31b-it    related  score   20 10 $REL
stage related-two      gemma-4-31b-it    related  two     20 10 $TWO
stage dilution-two     gemma-4-31b-it    dilution two     20 10 $K07
stage dilution         gemma-4-31b-it    dilution score   20 10 $DIL
stage dilution-verdict deepseek-v4-flash dilution verdict 20 12 $DIL
stage dilution-verdict gemma-4-31b-it    dilution verdict 20 10 $DIL
stage verdict-malt     deepseek-v4-flash malt     verdict 20 12 $MALT
stage verdict-malt     gemma-4-31b-it    malt     verdict 20 10 $MALT
stage related-verdict  deepseek-v4-flash related  verdict 20 12 $R7
stage related-verdict  gemma-4-31b-it    related  verdict 20 10 $R7
