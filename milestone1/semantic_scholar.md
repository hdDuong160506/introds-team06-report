# Semantic Scholar Reference Collection

## Objective and Input

The Semantic Scholar stage enriches the arXiv working corpus with metadata for
the documents cited by each assigned publication. The production workflow
reviewed here is `src/m1_crawling/colab_s2_references.ipynb` in
`arXir_project-main.zip`, alongside Dat's updated technical document.

It reads existing arXiv checkpoints and does not download the LaTeX sources
again. One reference lookup is initiated per uncached publication, rather than
per arXiv version; retries can generate additional HTTP requests. The resulting
reference pool supports later matching, but no BibTeX-to-reference matching is
performed in this stage.

```text
arXiv batch checkpoints
    -> read papers.jsonl and normalize publication IDs
    -> load valid per-publication reference caches
    -> request Semantic Scholar for uncached publications
    -> normalize and save all received reference records
    -> filter arXiv-bearing references, deduplicate and validate tables
```

## Loading arXiv Checkpoints

The notebook discovers `batch_*.json` markers and opens the corresponding
`.tar.gz` archives. `_read_jsonl_from_archive()` reads `papers.jsonl` without
extracting the entire source corpus. `load_all_papers_from_all_batches()`
normalizes IDs, merges metadata by base ID, sorts publications and writes
`tables/papers.json`. For repeated IDs, the later record read replaces the
earlier record.

All available publication metadata is used, including publications whose TeX
source is missing or whose source download failed. Source availability and
Semantic Scholar indexing are different outcomes.

The loader prints missing and extra IDs relative to the assigned range. This is
currently a warning, not an enforced filter of extra IDs. Missing/corrupt input
archives are reported and skipped. The loader does not independently verify the
checkpoint checksum or all manifest contents, so input completeness must also
be checked against the arXiv exports.

## API Requests and Returned Fields

The notebook constructs:

```text
https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}
```

`S2_FIELDS` requests `references.title`, `references.authors`, `references.year`,
`references.publicationDate`, `references.venue` and `references.externalIds`.
The mapper also reads the reference's `paperId` when returned, storing it as
`ref_s2_id`. The document's example query explicitly lists `references.paperId`,
whereas the supplied configuration does not list that field separately; the
description here follows the actual configuration.

`_resolve_api_key()` obtains the optional key from its argument or `S2_API_KEY`.
The request attaches it as `x-api-key`. Credentials are not included in report
data or code excerpts.

The notebook's status-aware wrapper calls the shared request helper:

```python
response = request_with_retry(
    "GET",
    url,
    headers=headers or None,
    params=params,
    timeout=60.0,
    max_retries=5,
)
```

This allows an initial attempt plus up to five retries. The helper retries
network exceptions and HTTP `429`, `500`, `502`, `503`, `504`, using increasing
backoff or a numeric `Retry-After`. HTTP-date `Retry-After` is not parsed by this
helper. Status backoff is capped at 120 seconds, so larger server-provided waits
are not preserved in full.

### Request pacing in the reviewed notebook

`semantic_scholar.py` has a different wrapper, `_s2_request()`, with configured
delays of 1 second with a key and 3.1 seconds without a key, plus a 60-second
cooldown after exhausted HTTP 429 retries. However, the production notebook
defines and calls `_s2_request_with_status()` directly. That path does not call
the module's delay/cooldown gate.

Publications run sequentially, but successful requests can be followed
immediately by the next publication. Retry backoff is present; proactive pacing
between all publications remains a correction requested from the module owner.
The configured library delay must not be described as an enforced notebook delay.

## Local Reference Normalization

`s2_ref_to_local_record()` converts each reference object into a local record:

- `arxiv_id`: normalized base ID of the citing publication.
- `ref_title`: reference title with leading/trailing whitespace removed.
- `ref_authors`: author names extracted from author objects, as `list[str]`.
- `ref_submission_date`: `publicationDate` truncated to a date string, otherwise
  the string representation of `year`, otherwise an empty string.
- `ref_arxiv_id`: normalized `externalIds.ArXiv`, or null when absent/invalid.
- `ref_s2_id`: reference `paperId` as a string, otherwise an empty string.
- `venue` and `year`: additional local metadata when available.

Despite its schema name, `ref_submission_date` here represents a Semantic
Scholar publication date or year, not a verified arXiv submission date.
Normalization removes supported prefixes/URLs and version suffixes and retains
old-style IDs such as `hep-th/9901001`. Format acceptance alone does not verify
that the target publication exists.

All normalized reference objects are retained locally, including references
without arXiv IDs. This preserves the collected fields, not the complete raw
API response or every field Semantic Scholar could provide.

## Status Classification and Empty Results

The notebook classifies publications as:

- `ok`: an accepted response was processed and saved successfully, or a cache
  was accepted. An empty reference list can be a successful result.
- `not_indexed`: HTTP 404 in the status-aware notebook wrapper.
- `failed`: other HTTP errors, network failures, invalid JSON, or failures in
  reference processing/writing. HTTP 400 is in this category.
- `invalid_id`: local ID normalization failed; no API request is sent.

The record includes `n_refs`, `n_arxiv`, `is_zero_ref`, `is_api_error`,
`is_invalid_id`, `from_cache`, `elapsed_s` and an error message. In the current
code, `is_api_error` follows `status == "failed"`, so it can include local
processing or write failures, not only API failures.

There is a pending payload-validation issue:

```python
raw_refs = payload.get("references") or []
```

A missing reference field can therefore become an empty successful cache. The
notebook does not require a correctly typed reference list before this step.
Consequently, reported zero-reference counts mean records accepted as empty by
the current implementation; they are not independently verified evidence that
the publications have no references. A stricter distinction between a valid
empty list and malformed payload is pending.

The separate library function `fetch_s2_references()` also returns `[]` on some
failures. This is not the status-aware notebook path used for the supplied
per-publication CSV and must not be used to infer identical error semantics.

## Cache and Resume

Each publication's normalized references are saved under a filesystem-safe name,
for example `2307.00001` becomes `reference/2307-00001.json`. The notebook writes
a temporary `.tmp` file and uses `os.replace()` to replace the final cache.

On rerun, a cache that parses as a list of dictionaries is accepted and records
`from_cache=True`; cached `[]` is also accepted. Corrupt files trigger another
lookup. Publications without a successful cache, including `not_indexed` and
`failed`, can be retried on a subsequent run.

Cache checks do not verify all fields, citing IDs or freshness. Empty caches
are not automatically refreshed. Per-publication saves survive interruptions,
but the run-level CSV/metrics are written at the end of the corresponding cell;
an interrupted run may have caches without a complete run summary. These
exports are overwritten on rerun rather than accumulated in a runtime ledger.

## Working Corpus and Output Tables

The notebook writes to a separate output directory from the arXiv checkpoints:

```text
references/
  range_<n>/
    reference/
      <publication-key>.json
    tables/
      papers.json
      references.json
      s2_crawl_records.csv
      metrics_s2_references.json
      validation_report.json
```

`papers` has one row per input publication with the fields `arxiv_id`, `title`,
`authors`, `submission_date`, `revised_dates`, `venue`. The reference stage
reuses this arXiv metadata rather than claiming to collect it again.

`s2_records_to_reference_rows()` filters local records to those with a usable
`ref_arxiv_id`. The exported `references` fields are `arxiv_id`, `ref_arxiv_id`,
`ref_title`, `ref_authors`, `ref_submission_date`, `ref_s2_id`. References without
an arXiv ID remain in the local working corpus.

The citing key `references.arxiv_id` associates a row with its source
publication. The cited `ref_arxiv_id` can be outside the assigned corpus; it
does not have to be a row in the group's `papers` table. Local JSON exports
are intermediate data, not a completed Hugging Face Parquet submission.

### Deduplication and validation

`dedupe_reference_rows()` keeps the first row for each tuple:

```python
(arxiv_id, ref_arxiv_id, ref_s2_id)
```

Two different publications citing the same reference retain separate rows.
This is identifier-based duplicate removal, not semantic reference matching or
field union across alternative descriptions of the same work.

`validate_m1_tables()` checks expected columns, selected required strings,
author-list types/non-emptiness, paper duplicates and duplicate reference keys.
It does not validate every date format or enforce cross-table foreign keys.
The notebook writes the tables even if issues are reported, saving the issues
to `validation_report.json` for review.

Dat's document reports one empty `ref_authors` issue at reference index 24532
in Range 4 and one at index 93254 in Range 5. These are findings of the current
validator. The source records and the agreed missing-metadata policy are
pending review; no author names are invented or records silently discarded.

## Measurements and Reported Results

`track_run("s2_references")` measures the crawl cell's wall duration and samples
the notebook process RSS approximately every 0.5 seconds. The region excludes
the earlier checkpoint loading and later table export/validation. Per-paper
`elapsed_s` measures the request wrapper, before normalization and cache writes.

The field `avg_s2_seconds_per_api_attempt` is calculated over fresh publication
lookups, each potentially including several HTTP retries. It is described in
this report as mean fetch time per freshly queried publication, not time per
individual HTTP attempt. Cache hits have `elapsed_s=0` in the CSV, although
reading caches contributes to cell wall time.

[Statistics](statistics.ipynb) presents the supplied final status/reference
counts. [Performance](performance.ipynb) presents the cache-heavy rerun timings
and RSS values. The reported 24,980 `ok` results include 24,811 cache hits;
therefore the 99.92% status rate is not the success rate of fresh API requests
in that measured rerun. Original run exports remain pending reconciliation.

Retry counts, HTTP 429 counts, corpus size, cold-crawl cumulative time and
cross-run history are not established by the supplied aggregates. The offline
tests in `tests/test_m1_pipeline.py` cover shared module behavior with mocked
network calls; they have been reviewed, not executed here, and do not by
themselves establish the correctness of the notebook-specific request wrapper.
