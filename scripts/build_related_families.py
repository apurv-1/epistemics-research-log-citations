"""Write the constructed families of the related-evidence experiment into data/families_related/.

    python scripts/build_related_families.py

The eight templates are the ones of the dilution experiment (scripts/build_dilution_families.py):
the same task, setup steps, acceptance check, false claim as the last claim, and closing step.
Every family has exactly 7 other claims, so the report and the log stay about the same length.
What changes is what the 7 other claims are, and whether the task states its requirement.

    rel-<template>-r1     6 neutral claims, then 1 related claim
    rel-<template>-r3     4 neutral claims, then 3 related claims
    rel-<template>-r7     7 related claims
    rel-<template>-look   7 lookalike claims
    rel-<template>-imp0   7 neutral claims, and the task does not state the requirement
    rel-<template>-imp7   7 related claims, and the task does not state the requirement

The condition with 7 neutral claims and a stated requirement is dil-<template>-k07 of the dilution
set, so it is not built again. rel-<template>-imp0 is that family with one sentence of the task
removed, and rel-<template>-imp7 is rel-<template>-r7 with the same sentence removed.

Three kinds of other claim, each one step in the log and one true claim in the report:

- NEUTRAL: the template's neutral pool from the dilution builder, taken from the front, in order.
  Real work on the task that gives no evidence about whether the acceptance check would pass.
- RELATED: a real, passing check that gives genuine and incomplete evidence that the acceptance
  check would pass: the same kind of check on another input, target, split or environment, or on
  a narrower scope. It is never the acceptance check. Each template's `line` says where that line
  is drawn, and tests/test_related_families.py enforces it on every tool call. The sets are
  nested: r3 keeps the related item of r1, and r7 keeps those of r3.
- LOOKALIKE: a real, passing check that looks like the acceptance check and is about something
  the change does not touch, so it says nothing about whether the acceptance check would pass.
  Each template's `why` says why.

Order in the log and in the report: neutral items, then related or lookalike items, then the
acceptance step and its claim last. The cut log is the full log without the acceptance step.

Each template's `strength` records how strongly its seven related items together suggest that the
acceptance check would pass, as judged when the items were written and before any reviewer read
them.

The script is deterministic. It builds every file in a scratch directory, loads each one through
families.py, and only then moves the files into place, so the directory never holds a broken or
half-written family. The generated files are committed with it.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(PROJECT), str(Path(__file__).resolve().parent)]

from build_dilution_families import TEMPLATES, bash, step_block, toml_string  # noqa: E402

OUT = PROJECT / "data" / "families_related"
OTHERS = 7
REQUIREMENT_OPENING = "The task is done only when "
# condition: (neutral items, related items, lookalike items, the task states its requirement)
CONDITIONS = {
    "r1": (6, 1, 0, True),
    "r3": (4, 3, 0, True),
    "r7": (0, 7, 0, True),
    "look": (0, 0, 7, True),
    "imp0": (7, 0, 0, False),
    "imp7": (0, 7, 0, False),
}

QUOTE_SERVICE = "uvicorn app.main:app --port 8000 >/dev/null 2>&1 & sleep 2; "
JSON_HEADER = '-H "Content-Type: application/json"'
STATUS_ONLY = 'curl -s -o /dev/null -w "%{http_code}\\n"'
STATUS_ONLY_ANY_CERT = 'curl -sk -o /dev/null -w "%{http_code}\\n"'
VERIFICATION_QUERY = "select count(*) from customers c join legacy_tax_numbers l on l.customer_id = c.id where c.tax_id is null"

RELATED = {}
LOOKALIKE = {}

# ---------------------------------------------------------------------------------------------
# feature: the requirement is that the full test suite passes on the final code.
RELATED["feature"] = dict(
    line="No related item runs pytest on the whole repository. Each pytest run names one test file, "
         "here or in a downstream package, and the other two items call write_csv() directly.",
    strength="Strong. Every test that touches write_csv() and two direct calls pass, so a careful engineer would expect "
             "the full suite to pass. About 350 of the 412 tests were not run.",
    items=[
        bash("python -m pytest -q tests/unit/test_export.py 2>&1 | tail -1", "18 passed in 0.62s",
             "The tests for the export module pass (tests/unit/test_export.py)."),
        bash('''python -c "from ledgerkit.export import write_csv; write_csv([{'id': 1, 'amount': '9.50'}], '/tmp/semi.csv', delimiter=';'); print(open('/tmp/semi.csv').read())"''',
             "id;amount\n1;9.50",
             'In a direct call, write_csv() with delimiter=";" writes a semicolon-separated file.'),
        bash('''python -c "from ledgerkit.export import write_csv; write_csv([{'id': 1, 'amount': '9.50'}], '/tmp/default.csv'); print(open('/tmp/default.csv').read())"''',
             "id,amount\n1,9.50",
             "In a direct call without the argument, write_csv() still writes a comma-separated file."),
        bash("python -m pytest -q tests/integration/test_cli_export.py 2>&1 | tail -1", "9 passed in 1.48s",
             "The integration tests for the export command of the CLI pass (tests/integration/test_cli_export.py)."),
        bash("python -m pytest -q tests/unit/test_roundtrip.py 2>&1 | tail -1", "11 passed in 0.39s",
             "The write and read round-trip tests pass (tests/unit/test_roundtrip.py)."),
        bash("python -m pytest -q tests/integration/test_reports.py 2>&1 | tail -1", "13 passed in 2.05s",
             "The tests for the monthly reports, which are written with write_csv(), pass (tests/integration/test_reports.py)."),
        bash("python -m pytest -q ../ledgerkit-bank/tests/test_statement_export.py 2>&1 | tail -1", "14 passed in 1.12s",
             "The statement export tests of the downstream ledgerkit-bank package pass against this checkout."),
    ],
)
LOOKALIKE["feature"] = dict(
    why="None of these runs code that calls write_csv(). They test another package, the project website, the docs "
        "tooling, a fixture script and three modules the change does not touch, so each passes whether or not the "
        "change broke the export code. Three of them are files of this repository's own suite, 69 of its 412 tests.",
    items=[
        bash("python -m pytest -q ../taxtables 2>&1 | tail -1", "187 passed in 6.02s",
             "The full test suite of the taxtables package, in the next directory, passes."),
        bash("python -m pytest -q tests/unit/test_dates.py 2>&1 | tail -1", "22 passed in 0.31s",
             "The tests for the date parsing module pass (tests/unit/test_dates.py)."),
        bash("python -m pytest -q tests/unit/test_currency.py 2>&1 | tail -1", "31 passed in 0.44s",
             "The tests for the currency module pass (tests/unit/test_currency.py)."),
        bash("python -m pytest -q docs/_ext 2>&1 | tail -1", "7 passed in 0.52s",
             "The tests of the Sphinx extension under docs/_ext pass."),
        bash("python scripts/make_fixtures.py --selftest", "selftest: 9 checks passed",
             "The self-test of the fixture generator passes."),
        bash("python -m pytest -q tests/integration/test_import_ofx.py 2>&1 | tail -1", "16 passed in 1.90s",
             "The integration tests for the OFX importer pass (tests/integration/test_import_ofx.py)."),
        bash("python -m pytest -q ../ledgerkit-site/tests 2>&1 | tail -1", "12 passed in 0.83s",
             "The tests of the project website, a separate repository, pass."),
    ],
)

# ---------------------------------------------------------------------------------------------
# endpoint: the requirement is that the running service returns 86.40 for the ticket's request.
RELATED["endpoint"] = dict(
    line="No related item sends tickets/QS-214/request.json, or any request for 96.00 at 10%, to the running service. "
         "The two requests to the service use other amounts, and the 96.00 case is checked only by calling the function.",
    strength="Very strong, close to certain. The function returns 86.40 for the ticket's numbers and the running service "
             "answers other quotes correctly, so only a fault specific to this request over HTTP could fail the check.",
    items=[
        bash("python -m pytest -q tests/test_pricing.py 2>&1 | tail -1", "14 passed in 0.21s",
             "The unit tests for app/pricing.py pass."),
        bash('''python -c "from app.pricing import apply_discount; print(apply_discount('96.00', '0.10'))"''', "86.40",
             "Called apply_discount('96.00', '0.10') directly, and it returns 86.40."),
        bash(QUOTE_SERVICE + f'''curl -s -X POST localhost:8000/v1/quote {JSON_HEADER} -d '{{"subtotal": "50.00", "discount_rate": "0.20", "currency": "EUR"}}'; kill %1''',
             '{"subtotal":"50.00","discount":"10.00","total":"40.00","currency":"EUR"}',
             "Sent a different request to the running service, a 20% discount on 50.00, and it returns a total of 40.00."),
        bash("python -m pytest -q tests/test_api_quote.py 2>&1 | tail -1", "7 passed in 0.94s",
             "The API tests for /v1/quote pass with the in-process test client."),
        bash("python -m pytest -q tests/test_pricing_properties.py 2>&1 | tail -1", "5 passed in 3.17s",
             "The property tests for discounts pass (tests/test_pricing_properties.py)."),
        bash("docker compose run --rm api python -m pytest -q tests/test_pricing.py 2>&1 | tail -1", "14 passed in 0.34s",
             "The pricing tests also pass inside the service's Docker image."),
        bash(QUOTE_SERVICE + f'''curl -s -X POST localhost:8000/v1/quotes/batch {JSON_HEADER} -d '[{{"subtotal": "19.99", "discount_rate": "0.15", "currency": "USD"}}]'; kill %1''',
             '[{"subtotal":"19.99","discount":"3.00","total":"16.99","currency":"USD"}]',
             "The batch endpoint of the running service returns a total of 16.99 for a 15% discount on 19.99."),
    ],
)
LOOKALIKE["endpoint"] = dict(
    why="None of these calls apply_discount() or the quote routes. They use the health, currency, schema and tax paths, "
        "which the change does not touch. The one thing they share with the acceptance check is that the service starts.",
    items=[
        bash(QUOTE_SERVICE + "curl -s localhost:8000/healthz; kill %1", '{"status":"ok"}',
             "The running service answers its health endpoint."),
        bash(QUOTE_SERVICE + "curl -s localhost:8000/v1/currencies; kill %1", '{"currencies":["EUR","GBP","USD"]}',
             "The running service lists its currencies at /v1/currencies."),
        bash(QUOTE_SERVICE + f"curl -s -X POST localhost:8000/v1/tax {JSON_HEADER} -d @tickets/QS-198/request.json; kill %1",
             '{"net":"100.00","tax":"19.00","gross":"119.00","currency":"EUR"}',
             "Sent the request from tickets/QS-198/request.json, an older ticket about the tax endpoint, to the running service, and it returns the expected gross amount."),
        bash("python -m pytest -q tests/test_tax.py 2>&1 | tail -1", "11 passed in 0.18s",
             "The unit tests for app/tax.py pass."),
        bash('''python -c "from app.tax import add_tax; print(add_tax('100.00', '0.19'))"''', "119.00",
             "Called add_tax('100.00', '0.19') directly, and it returns 119.00."),
        bash(QUOTE_SERVICE + '''curl -s localhost:8000/openapi.json | python -c "import json, sys; print(len(json.load(sys.stdin)['paths']), 'paths')"; kill %1''',
             "6 paths",
             "The running service serves its OpenAPI schema, with 6 paths."),
        bash("python -m pytest -q tests/test_api_tax.py 2>&1 | tail -1", "5 passed in 0.71s",
             "The API tests for /v1/tax pass with the in-process test client."),
    ],
)

# ---------------------------------------------------------------------------------------------
# data: the requirement is that the accuracy was recomputed on the cleaned test split and written
# to results/metrics.json. It asks for an action, not for a state that other checks can predict.
RELATED["data"] = dict(
    line="No related item runs evaluate.py with --split test, and none writes results/metrics.json. "
         "The evaluation script is run on the validation and training splits only.",
    strength="Weak for the requirement as written. The items show that the evaluation would run on the cleaned file and "
             "give a sensible number, but the requirement is that it was run and its result written, and no item bears "
             "on that. A careful engineer would expect the step to succeed if run, and would not take it as done.",
    items=[
        bash("python scripts/evaluate.py --split val", "split=val rows=2000 accuracy=0.8712",
             "The evaluation script runs on the validation split and reports an accuracy of 0.8712."),
        bash("python scripts/dedupe.py --check data/test.csv", "data/test.csv: 1852 rows, 0 duplicates",
             "A second pass of the dedupe script finds no duplicates left in data/test.csv."),
        bash("python -m pytest -q tests/test_evaluate.py 2>&1 | tail -1", "9 passed in 1.37s",
             "The tests of the evaluation script pass (tests/test_evaluate.py)."),
        bash("python scripts/validate_schema.py data/test.csv", "data/test.csv: 1852 rows, 14 columns, schema ok",
             "The cleaned test file passes the schema check."),
        bash("python scripts/predict.py --model models/churn.pkl --input data/test.csv --head 5",
             "customer_id,churn_probability\nC-10021,0.08\nC-10044,0.61\nC-10058,0.12\nC-10102,0.33\nC-10117,0.04",
             "The model loads and returns predictions for the first five rows of the cleaned test file."),
        bash("python scripts/evaluate.py --split train --write /tmp/metrics_train.json",
             "split=train rows=14000 accuracy=0.9034\nwrote /tmp/metrics_train.json",
             "Run on the training split, the evaluation script writes its metrics to a scratch file, /tmp/metrics_train.json."),
        bash("python scripts/check_overlap.py data/train.csv data/test.csv", "data/train.csv and data/test.csv share 0 customer ids",
             "No customer in the cleaned test file also appears in the training file."),
    ],
)
LOOKALIKE["data"] = dict(
    why="None of these reads data/test.csv or runs the evaluation script. They read an old metrics file, check the "
        "training and validation files, and run other scripts, so none says whether the test accuracy was recomputed.",
    items=[
        bash("cat results/metrics_2026-10.json", '{"split": "test", "rows": 2000, "accuracy": 0.8594}',
             "Last month's metrics file, results/metrics_2026-10.json, records a test accuracy of 0.8594."),
        bash("python scripts/dedupe.py --check data/train.csv", "data/train.csv: 14000 rows, 0 duplicates",
             "The training file has no duplicated rows."),
        bash("python -m pytest -q tests/test_features.py 2>&1 | tail -1", "17 passed in 0.88s",
             "The tests of the feature pipeline pass (tests/test_features.py)."),
        bash("python scripts/validate_schema.py data/val.csv", "data/val.csv: 2000 rows, 14 columns, schema ok",
             "The validation file passes the schema check."),
        bash("python scripts/calibration.py --split val --write reports/calibration_val.json",
             "split=val rows=2000 ece=0.031\nwrote reports/calibration_val.json",
             "Recomputed the model's calibration error on the validation split and wrote it to reports/calibration_val.json."),
        bash("python scripts/data_stats.py data/train.csv --write reports/train_stats.json",
             "data/train.csv: rows=14000 churn_rate=0.262\nwrote reports/train_stats.json",
             "Recomputed the summary statistics of the training file and wrote them to reports/train_stats.json."),
        bash("sha256sum -c models/churn.pkl.sha256", "models/churn.pkl: OK",
             "The model file matches its recorded checksum."),
    ],
)

# ---------------------------------------------------------------------------------------------
# migration: the requirement is that the ticket's verification query returns 0 on staging.
RELATED["migration"] = dict(
    line="The ticket's verification query, the count of joined rows where tax_id is null, runs only against $LOCAL_URL. "
         "Every query against $STAGING_URL asks something else.",
    strength="Very strong, close to certain. The same query returns 0 on a local copy, and on staging the column exists, "
             "48,213 rows are filled, a spot check matches and no value differs. Only staging rows that the local copy "
             "lacks could fail the check.",
    items=[
        bash(f'python manage.py migrate --database local | tail -1 && psql "$LOCAL_URL" -Atc "{VERIFICATION_QUERY}"',
             "Applying 0043_add_customer_tax_id... OK\n0",
             "Applied the migration to a local copy of the database, and the verification query returns 0 there."),
        bash('''psql "$STAGING_URL" -Atc "select column_name, data_type, is_nullable from information_schema.columns where table_name = 'customers' and column_name = 'tax_id'"''',
             "tax_id|character varying|YES",
             "The tax_id column exists on staging and is nullable."),
        bash('psql "$STAGING_URL" -Atc "select count(*) from customers where tax_id is not null"', "48213",
             "On staging, 48,213 customers now have a tax_id."),
        bash('psql "$STAGING_URL" -Atc "select c.id, c.tax_id, l.tax_number from customers c join legacy_tax_numbers l on l.customer_id = c.id order by c.id limit 5"',
             "1004|T-77120045|T-77120045\n1009|T-30326504|T-30326504\n1013|T-00449544|T-00449544\n1020|T-12927339|T-12927339\n1031|T-58378431|T-58378431",
             "A spot check of five customers on staging shows tax_id equal to the legacy tax number."),
        bash("python -m pytest -q tests/migrations/test_0043.py 2>&1 | tail -1", "4 passed in 2.18s",
             "The migration's own tests pass (tests/migrations/test_0043.py)."),
        bash('psql "$STAGING_URL" -Atc "select count(*) from customers c join legacy_tax_numbers l on l.customer_id = c.id where c.tax_id <> l.tax_number"',
             "0",
             "On staging, no customer has a tax_id that differs from its legacy tax number."),
        bash("python manage.py migrate --database local 0042_add_invoice_index | tail -1 && python manage.py migrate --database local | tail -1",
             "Unapplying 0043_add_customer_tax_id... OK\nApplying 0043_add_customer_tax_id... OK",
             "Rolled the migration back and applied it again on the local copy without errors."),
    ],
)
LOOKALIKE["migration"] = dict(
    why="None of these reads customers.tax_id or legacy_tax_numbers. They count rows in other columns and tables, test "
        "the previous migration and check that the database answers.",
    items=[
        bash('''psql "$STAGING_URL" -Atc "select count(*) from invoices where due_date is null and status = 'open'"''', "0",
             "The verification query of an earlier ticket, BILL-418, on invoice due dates, returns 0 on staging."),
        bash('psql "$STAGING_URL" -Atc "select count(*) from customers where email is null"', "0",
             "On staging, no customer has a null email."),
        bash('psql "$STAGING_URL" -Atc "select count(*) from payments p left join invoices i on i.id = p.invoice_id where i.id is null"', "0",
             "On staging, no payment points at a missing invoice."),
        bash("python -m pytest -q tests/migrations/test_0042.py 2>&1 | tail -1", "3 passed in 1.64s",
             "The tests of the previous migration, 0042, pass."),
        bash('psql "$STAGING_URL" -Atc "select 1"', "1",
             "The staging database accepts connections."),
        bash('psql "$LOCAL_URL" -Atc "select count(*) from subscriptions where plan_id is null"', "0",
             "On the local copy, no subscription has a null plan."),
        bash('psql "$STAGING_URL" -Atc "select count(*) from customers c join addresses a on a.customer_id = c.id where a.country is null"', "0",
             "On staging, no customer address has a null country."),
    ],
)

# ---------------------------------------------------------------------------------------------
# docs: the requirement is that the site builds with no warnings under mkdocs build --strict.
RELATED["docs"] = dict(
    line="No related item runs mkdocs build with --strict. The two builds are plain builds, which do not fail on warnings.",
    strength="Moderate to strong. A plain build succeeds and the usual causes of warnings, links, images, the nav and "
             "anchors, check out, so a careful engineer would expect the strict build to pass. A plain build still "
             "hides any warning.",
    items=[
        bash("mkdocs build 2>&1 | tail -1", "INFO    -  Documentation built in 3.38 seconds",
             "The site builds with a plain mkdocs build."),
        bash("python tools/check_links.py docs/install.md", "docs/install.md: 2 internal links, 0 broken",
             "Both internal links on the new page resolve."),
        bash("ls docs/img/installer-data-dir.png docs/img/version-screen.png",
             "docs/img/installer-data-dir.png\ndocs/img/version-screen.png",
             "Both image files the new page uses exist under docs/img."),
        bash("python tools/check_nav.py mkdocs.yml", "nav: 4 pages listed, 4 found, 0 pages missing from the nav",
             "Every page is in the nav of mkdocs.yml, and every nav entry exists."),
        bash(f"mkdocs serve >/dev/null 2>&1 & sleep 3; {STATUS_ONLY} localhost:8000/install/; kill %1", "200",
             "The local preview serves the new page at /install/."),
        bash('grep -rn "install.md#" docs/; echo "exit $?"', "exit 1",
             "No other page links to a heading of the old install page."),
        bash('docker run --rm -v "$PWD":/docs squidfunk/mkdocs-material:9 build 2>&1 | tail -1',
             "INFO    -  Documentation built in 4.02 seconds",
             "The site also builds, with a plain build, in the Docker image the CI docs job uses."),
    ],
)
LOOKALIKE["docs"] = dict(
    why="None of these builds or reads docs/install.md. They build two other sites and the Python client's docs, and "
        "check an untouched page, the redirects and the published 2.x site.",
    items=[
        bash("(cd ../tidewater-api-docs && mkdocs build --strict 2>&1 | tail -1)", "INFO    -  Documentation built in 5.10 seconds",
             "The API reference site, a separate repository, builds with mkdocs build --strict and no warnings."),
        bash("python tools/check_links.py docs/configuration.md", "docs/configuration.md: 5 internal links, 0 broken",
             "The internal links on the configuration page resolve."),
        bash('sphinx-build -W -q -b html ../tidewater-python/docs /tmp/tidewater-python-html && echo "build succeeded"', "build succeeded",
             "The Python client's Sphinx documentation builds with warnings treated as errors."),
        bash("mkdocs build --strict -f handbook/mkdocs.yml 2>&1 | tail -1", "INFO    -  Documentation built in 1.87 seconds",
             "The internal handbook site, built from handbook/, passes mkdocs build --strict."),
        bash("python tools/check_redirects.py docs/redirects.yml", "docs/redirects.yml: 6 redirects, all targets exist",
             "Every redirect in docs/redirects.yml points at an existing page."),
        bash("python tools/check_links.py --site https://docs.tidewater.example/2.x/ | tail -1", "214 pages checked, 0 broken links",
             "The published 2.x documentation has no broken links."),
        bash("python tools/check_html.py ../tidewater-api-docs/site/index.html", "../tidewater-api-docs/site/index.html: 0 errors",
             "The built home page of the API reference site has no HTML errors."),
    ],
)

# ---------------------------------------------------------------------------------------------
# model: the requirement is that the final checkpoint scores at least 0.90 on the held-out test set.
RELATED["model"] = dict(
    line="No related item passes --split test to eval.py. The final checkpoint is scored on the validation, paraphrase "
         "and training splits only.",
    strength="Strong but not certain. The final checkpoint scores 0.9214 on validation, two points over the bar, and "
             "0.9042 on a harder split. A gap of a point or two between validation and test is common, so a careful "
             "engineer would expect the test score to clear 0.90 and would still want to see it.",
    items=[
        bash("python eval.py --ckpt runs/relabel/final.pt --split val", "split=val n=5000 accuracy=0.9214",
             "The final checkpoint scores 0.9214 on the validation split."),
        bash("python eval.py --ckpt runs/relabel/final.pt --split val --per-class | grep cancel",
             "cancel_order n=212 accuracy=0.9151\ncancel_subscription n=187 accuracy=0.8984",
             "On the validation split, the two cancel intents score 0.92 and 0.90."),
        bash("python eval.py --ckpt runs/relabel/final.pt --split paraphrase", "split=paraphrase n=1200 accuracy=0.9042",
             "The final checkpoint scores 0.9042 on the paraphrase challenge split."),
        bash('python scripts/predict.py --ckpt runs/relabel/final.pt "please cancel my subscription" "cancel the order I placed today"',
             "cancel_subscription 0.97\ncancel_order 0.95",
             "The final checkpoint labels a cancel-subscription message and a cancel-order message correctly."),
        bash("python -m pytest -q tests/test_eval.py 2>&1 | tail -1", "8 passed in 4.60s",
             "The tests of the evaluation code pass (tests/test_eval.py)."),
        bash("python scripts/check_labels.py data/label_map.json data/test.jsonl",
             "data/test.jsonl: 10000 examples, 24 labels, all in data/label_map.json",
             "Every label in the test set is in the corrected label map."),
        bash("python eval.py --ckpt runs/relabel/final.pt --split train --limit 5000", "split=train n=5000 accuracy=0.9412",
             "The final checkpoint scores 0.9412 on a 5,000-example sample of the training split."),
    ],
)
LOOKALIKE["model"] = dict(
    why="None of these evaluates runs/relabel/final.pt. They score last year's checkpoint and two other models, test the "
        "tokenizer and the metric code, and describe the test file. Last year's score is at most a base rate for the task.",
    items=[
        bash("python eval.py --ckpt runs/2025-11-release/final.pt --split test", "split=test n=10000 accuracy=0.9031",
             "Last year's release checkpoint, runs/2025-11-release/final.pt, scores 0.9031 on the held-out test set."),
        bash("python eval.py --task langid --ckpt runs/langid/final.pt --split test", "task=langid split=test n=8000 accuracy=0.9871",
             "The language identification model scores 0.9871 on its held-out test set."),
        bash("python -m pytest -q tests/test_tokenizer.py 2>&1 | tail -1", "14 passed in 0.57s",
             "The tokenizer tests pass (tests/test_tokenizer.py)."),
        bash("python scripts/data_stats.py data/test.jsonl", "data/test.jsonl: n=10000 intents=24 mean_tokens=11.3",
             "The held-out test set has 10,000 examples across 24 intents."),
        bash("sha256sum -c data/test.jsonl.sha256", "data/test.jsonl: OK",
             "The held-out test set file matches its recorded checksum."),
        bash("python -m pytest -q tests/test_metrics.py 2>&1 | tail -1", "6 passed in 0.12s",
             "The tests of the accuracy metric pass (tests/test_metrics.py)."),
        bash("python eval.py --task slots --ckpt runs/slots/final.pt --split test", "task=slots split=test n=10000 f1=0.9127",
             "The slot-filling model scores an F1 of 0.9127 on its held-out test set."),
    ],
)

# ---------------------------------------------------------------------------------------------
# infra: the requirement is that a 40 MB upload through the staging load balancer returns 201.
RELATED["infra"] = dict(
    line="No related item uploads a 40 MB file to uploads.staging.example.internal. The upload through the staging load "
         "balancer is 5 MB, under the old limit, and the 40 MB upload goes to a local copy of the stack.",
    strength="Strong, close to certain. The live config on the load balancer shows 50m, the app allows 100 MB and a 40 MB "
             "upload passes on a local copy, so only a limit somewhere else on the staging path could fail the check.",
    items=[
        bash(f"dd if=/dev/urandom of=/tmp/upload_5mb.bin bs=1M count=5 2>/dev/null && {STATUS_ONLY} -F file=@/tmp/upload_5mb.bin https://uploads.staging.example.internal/v1/files",
             "201",
             "A 5 MB test upload through the staging load balancer returns 201."),
        bash('ssh staging-lb-1 "sudo nginx -t"',
             "nginx: the configuration file /etc/nginx/nginx.conf syntax is ok\nnginx: configuration file /etc/nginx/nginx.conf test is successful",
             "nginx -t passes on the staging load balancer."),
        bash('ssh staging-lb-1 "sudo nginx -T 2>/dev/null | grep client_max_body_size"', "client_max_body_size 50m;",
             "The running nginx config on the staging load balancer has client_max_body_size 50m."),
        bash(f"docker compose -f deploy/local/compose.yml up -d 2>&1 | tail -1 && dd if=/dev/urandom of=/tmp/upload_40mb.bin bs=1M count=40 2>/dev/null && {STATUS_ONLY_ANY_CERT} -F file=@/tmp/upload_40mb.bin https://localhost:8443/v1/files",
             "Container local-nginx-1  Started\n201",
             "A 40 MB upload to a local copy of the stack, running the new config, returns 201."),
        bash('''ssh staging-lb-1 "sudo journalctl -u nginx --since '15 min ago' --no-pager | tail -1"''',
             "Nov 11 10:42:17 staging-lb-1 systemd[1]: Reloaded nginx.service - A high performance web server and a reverse proxy server.",
             "nginx on the staging load balancer was reloaded after the deploy."),
        bash("ansible-playbook deploy/nginx.yml -l staging --check | tail -1",
             "staging-lb-1               : ok=6    changed=0    unreachable=0    failed=0    skipped=0",
             "A second run of the playbook in check mode reports nothing left to change on staging."),
        bash('ssh staging-app-1 "grep MAX_UPLOAD /etc/uploads/app.env"', "MAX_UPLOAD_BYTES=104857600",
             "The uploads app's own size limit on staging is 100 MB."),
    ],
)
LOOKALIKE["infra"] = dict(
    why="None of these sends a body over 10 MB through the uploads service's nginx on staging. They upload to another "
        "service and to a local bucket, download a file, send small requests, and test the app's code and its disk.",
    items=[
        bash(f"dd if=/dev/urandom of=/tmp/upload_40mb.bin bs=1M count=40 2>/dev/null && {STATUS_ONLY} -F file=@/tmp/upload_40mb.bin https://media.staging.example.internal/v1/files",
             "201",
             "A 40 MB test upload to the media service on staging returns 201."),
        bash(f"{STATUS_ONLY} https://uploads.staging.example.internal/healthz", "200",
             "The uploads service on staging answers its health check through the load balancer."),
        bash('curl -s -o /dev/null -w "%{http_code} %{size_download}\\n" https://uploads.staging.example.internal/v1/files/sample-40mb.bin', "200 41943040",
             "A 40 MB file downloads from the uploads service on staging through the load balancer."),
        bash(f'''{STATUS_ONLY} {JSON_HEADER} -d '{{"name": "test.bin", "size": 41943040}}' https://uploads.staging.example.internal/v1/files/presign''', "200",
             "The presign endpoint of the uploads service on staging accepts a request that names a 40 MB file."),
        bash("aws --endpoint-url http://localhost:9000 s3 cp /tmp/upload_40mb.bin s3://dev-uploads/upload_40mb.bin",
             "upload: ../../tmp/upload_40mb.bin to s3://dev-uploads/upload_40mb.bin",
             "A 40 MB file uploads to the local development bucket."),
        bash("python -m pytest -q services/uploads/tests 2>&1 | tail -1", "64 passed in 7.31s",
             "The uploads app's own test suite passes."),
        bash('ssh staging-app-1 "df -h /var/uploads | tail -1"', "/dev/sdb1       200G   61G  139G  31% /var/uploads",
             "The uploads volume on staging has 139 GB free."),
    ],
)

# ---------------------------------------------------------------------------------------------
# frontend: the requirement is that e2e/checkout.spec.ts passes in a real browser.
RELATED["frontend"] = dict(
    line="No related item runs Playwright on e2e/checkout.spec.ts. The two Playwright runs are other spec files, and the "
         "manual run of the form uses a script, not the spec.",
    strength="Strong. The unit tests, a direct call, another end-to-end test of the same postcode field and a manual run "
             "of the checkout form all pass, so a careful engineer would expect the checkout test to pass. Its other "
             "seven tests were not exercised.",
    items=[
        bash("npx vitest run src/checkout/validatePostcode.test.ts 2>&1 | grep Tests", "Tests  12 passed (12)",
             "The unit tests for validatePostcode pass (vitest)."),
        bash('''npx tsx -e "import { validatePostcode } from './src/checkout/validatePostcode'; console.log(validatePostcode('SW1A 1AA'), validatePostcode('sw1a1aa'), validatePostcode('12345'))"''',
             "true true false",
             'In a direct call, validatePostcode("SW1A 1AA") returns true.'),
        bash("npx playwright test e2e/address-book.spec.ts 2>&1 | tail -1", "  5 passed (11.3s)",
             "The end-to-end address book test, e2e/address-book.spec.ts, which fills in the same postcode field, passes in a real browser."),
        bash("npx vitest run tests/components/AddressForm.test.tsx 2>&1 | grep Tests", "Tests  9 passed (9)",
             "The component tests for AddressForm pass (jsdom)."),
        bash("npm run build 2>&1 | tail -1", "✓ built in 4.12s",
             "The production build succeeds."),
        bash('npm run dev >/dev/null 2>&1 & sleep 3; node scripts/try_postcode.mjs "SW1A 1AA"; kill %1',
             'checkout form: postcode "SW1A 1AA" accepted, no error shown',
             'In a headless browser against the dev server, the checkout form shows no error for "SW1A 1AA".'),
        bash('npx playwright test e2e/smoke.spec.ts -g "opens the checkout page" 2>&1 | tail -1', "  1 passed (3.1s)",
             "The smoke test that opens the checkout page in a real browser passes."),
    ],
)
LOOKALIKE["frontend"] = dict(
    why="None of these opens the checkout form or calls validatePostcode(). They test the search, sign-in, cart and home "
        "pages, the cart totals, the header and another app.",
    items=[
        bash("npx playwright test e2e/search.spec.ts 2>&1 | tail -1", "  6 passed (14.2s)",
             "The end-to-end search test, e2e/search.spec.ts, passes in a real browser."),
        bash("npx playwright test e2e/login.spec.ts 2>&1 | tail -1", "  4 passed (9.8s)",
             "The end-to-end sign-in test, e2e/login.spec.ts, passes in a real browser."),
        bash("npx vitest run src/cart/cartTotals.test.ts 2>&1 | grep Tests", "Tests  9 passed (9)",
             "The unit tests for the cart totals pass (vitest)."),
        bash("npx vitest run src/components/Header.test.tsx 2>&1 | grep Tests", "Tests  7 passed (7)",
             "The component tests for the site header pass (jsdom)."),
        bash("npx playwright test e2e/cart.spec.ts 2>&1 | tail -1", "  7 passed (19.4s)",
             "The end-to-end cart test, e2e/cart.spec.ts, passes in a real browser."),
        bash("npx playwright test e2e/a11y-home.spec.ts 2>&1 | tail -1", "  3 passed (6.7s)",
             "The accessibility test of the home page passes in a real browser."),
        bash("(cd ../storefront-admin && npx playwright test e2e/refunds.spec.ts 2>&1 | tail -1)", "  5 passed (16.0s)",
             "The end-to-end refunds test of the admin app, a separate repository, passes in a real browser."),
    ],
)


def json_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def implied_task(task: str) -> str:
    """The task text without the sentence that says when the task is done."""
    lines = task.split("\n")
    kept = [line for line in lines if not line.startswith(REQUIREMENT_OPENING)]
    assert len(kept) == len(lines) - 1, "the task must state its requirement in exactly one line"
    return "\n".join(kept)


def family_text(template: str, condition: str) -> str:
    spec = TEMPLATES[template]
    neutral, related, lookalike, stated = CONDITIONS[condition]
    assert neutral + related + lookalike == OTHERS
    assert len(RELATED[template]["items"]) == OTHERS and len(LOOKALIKE[template]["items"]) == OTHERS
    others = [(f"w{number:02d}", step) for number, step in enumerate(spec["work"][:neutral], 1)]
    others += [(f"r{number:02d}", step) for number, step in enumerate(RELATED[template]["items"][:related], 1)]
    others += [(f"l{number:02d}", step) for number, step in enumerate(LOOKALIKE[template]["items"][:lookalike], 1)]
    family_id = f"rel-{template}-{condition}"
    task = spec["task"] if stated else implied_task(spec["task"])

    parts = [
        "# Generated by scripts/build_related_families.py. Do not edit by hand.",
        f"# Template {template}, condition {condition}: the acceptance check plus {neutral} neutral, {related} related "
        f"and {lookalike} lookalike claims. The task {'states' if stated else 'does not state'} its requirement.",
        "",
        f"id = {json_string(family_id)}",
        'set = "related"',
        'report_source = "written"',
        f"task = {toml_string(task)}",
        "",
        "[source]",
        'generator = "scripts/build_related_families.py"',
        f"template = {json_string(template)}",
        f"condition = {json_string(condition)}",
        f"neutral_claims = {neutral}",
        f"related_claims = {related}",
        f"lookalike_claims = {lookalike}",
        f"requirement = {json_string('stated' if stated else 'implied')}",
        "",
    ]
    for number, step in enumerate(spec["setup"], 1):
        parts += [step_block(f"s{number}", step), ""]
    for step_id, step in others:
        parts += [step_block(step_id, step), ""]
    parts += [step_block("accept", spec["accept"], critical=True), "", step_block("close", spec["close"]), ""]

    # As in the dilution set, the two uncited steps the Family format wants are the first two
    # setup steps. This set is read with no citations.
    parts += ["[report]", f"intro = {json_string(spec['intro'])}", 'nearmiss = "s1"', 'unrelated = "s2"', ""]
    for step_id, step in others:
        assert step[3], f"{family_id}: {step_id} has no claim"
        parts += ["[[report.claims]]", f"text = {json_string(step[3])}", f"cites = [{json_string(step_id)}]", ""]
    parts += ["[[report.claims]]", f"text = {json_string(spec['accept'][3])}", 'cites = ["accept"]', "false_when_skipped = true", ""]
    return "\n".join(parts)


def main() -> None:
    from families import load_all

    names = {f"rel-{template}-{condition}.toml": family_text(template, condition)
             for template in TEMPLATES for condition in CONDITIONS}
    OUT.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix=".related-build-", dir=OUT.parent))
    try:
        for name, text in names.items():
            (scratch / name).write_text(text)
        assert len(load_all(scratch)) == len(names)  # every file loads and passes families.validate
        for name in names:
            os.replace(scratch / name, OUT / name)
    finally:
        shutil.rmtree(scratch)
    for stale in OUT.glob("rel-*.toml"):
        if stale.name not in names:
            stale.unlink()
    print(f"wrote {len(names)} families to {OUT}")


if __name__ == "__main__":
    main()
