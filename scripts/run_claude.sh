#!/bin/bash
# Run the stronger reviewers' readings in the order RELATED.md fixes ("Changes during the run").
#
#   scripts/run_claude.sh
#
# Claude Sonnet 5.5 first, then Claude Opus 5.5. A run that stops can be started again: readings
# that already have a valid answer are skipped.
set -u
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-${TMPDIR:-/tmp}/uv-cache}"
TEMPLATES="data docs endpoint feature frontend infra migration model"
R7=""; K07=""
for t in $TEMPLATES; do R7="$R7 rel-$t-r7"; K07="$K07 dil-$t-k07"; done

read_set() {  # model set arm out families...
  local model="$1" set="$2" arm="$3" out="$4"; shift 4
  uv run --offline python claude_reviewer.py --set "$set" --instructions "$arm" --models "$model" --readings 3 \
    --workers 3 --out "results/raw/$out" --run ${@:+--families "$@"} >> results/claude.log 2>&1
  echo "$(date '+%H:%M') $model $set $arm: $(tail -1 results/claude.log | cut -c1-150)"
}

for model in sonnet opus; do
  read_set "$model" dilution score claude-dilution.jsonl $K07
  read_set "$model" related  score claude-related.jsonl  $R7
  read_set "$model" dilution two   claude-dilution.jsonl $K07
  read_set "$model" related  two   claude-related.jsonl  $R7
  read_set "$model" malt     score claude-malt.jsonl
done
