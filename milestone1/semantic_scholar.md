# Semantic Scholar Reference Collection

## Objective and Input

The Semantic Scholar stage enriches the arXiv working corpus with metadata for
the documents cited by each assigned publication. Its input is the publication
metadata stored in the arXiv batch checkpoints.

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

## Design Rationale and Result Scope

Reference lookup operates at publication level because M1's reference table
associates each cited work with a citing base arXiv ID. Using arXiv metadata as
input keeps the two stages connected without downloading sources a second time.
Keeping references without arXiv IDs locally preserves the collected metadata,
while the exported matching pool uses the arXiv-bearing subset.

Per-publication caches provide resumability. They also change how a rerun must
be evaluated: accepted saved records, fresh lookup outcomes and fresh HTTP
attempts are different quantities. The results pages use those distinctions
when presenting status rates and timing.

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

## API Requests and Returned Fields

The notebook constructs:

```text
https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}
```

Collected reference fields include title, authors, year, publication date,
Semantic Scholar `paperId` and `externalIds.ArXiv`. The publication ID in the
request identifies the citing paper; each returned object describes a cited
work.

HTTP requests use timeouts and retries for network exceptions and HTTP `429`,
`500`, `502`, `503` and `504`. The updated metrics record the configured delays
as `s2_min_delay_sec=1.0`, `s2_min_delay_unauth_sec=3.1` and
`s2_429_cooldown_sec=60.0`.

The five measured reruns recorded 34 HTTP attempts, including 15 retries and
15 HTTP 429 responses, while processing 19 uncached publications. Attempt
counters describe the request history; publication status describes the final
outcome for each input.

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

The exported records classify publications as:

- `ok`: a response was processed and saved successfully, or an existing cache
  was accepted. A saved empty reference list is included in this category.
- `not_indexed`: HTTP 404 in the delivered crawl records.
- `failed`: a final technical or processing failure.
- `invalid_id`: local ID normalization failed; no API request is sent.

Each CSV row records the publication ID, run ID, status, reference counts,
cache flag, error details and HTTP attempt/retry/429 counters. `elapsed_s`
is recorded for fresh publication lookups; cache hits leave it blank.

In the 11 November exports, 24,981 publications were accepted from cache and
19 fresh lookups ended as `not_indexed`. The saved records include 1,881 empty
reference lists. These counts describe the stored lists for the citing
publications.

## Cache and Resume

Each publication's normalized references are saved under a filesystem-safe name,
for example `2307.00001` becomes `reference/2307-00001.json`. The notebook writes
a temporary `.tmp` file and uses `os.replace()` to replace the final cache.

On rerun, a cache that parses as a list of dictionaries is accepted and records
`from_cache=True`; cached `[]` is also accepted. Corrupt files trigger another
lookup. Publications without a successful cache, including `not_indexed` and
`failed`, can be retried on a subsequent run.

Per-publication files preserve completed reference collections between sessions.
The per-range CSV and metrics summarize the corresponding run, identified by
the same `range_id` and `run_id` as its validation report.

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
does not have to be a row in the group's `papers` table.

### Deduplication and validation

`dedupe_reference_rows()` keeps the first row for each tuple:

```python
(arxiv_id, ref_arxiv_id, ref_s2_id)
```

Two different publications citing the same reference retain separate rows.
This is identifier-based duplicate removal, not semantic reference matching or
field union across alternative descriptions of the same work.

The updated validation reports contain 5,000 paper rows per range and
449,591 reference rows in total. For every range, the reported reference count
before identifier-based deduplication equals the count after it.

All five validation reports have `ok=true` and zero issues. Range 4 records
an empty `ref_authors` list at reference index 24532; Range 5 records one at
index 93254. The validator retains these rows and records a metadata warning
under its documented policy allowing empty author lists.

## Measurements and Reported Results

The updated exports distinguish the fresh-lookup timer, the crawl-loop timer
and the notebook-cell timer. Process RSS is sampled every 0.5 seconds, and the
reference-cache directory size is sampled every 30 seconds. Dat's final output
measurement sums the files in each range directory after table export.

[Statistics](statistics.ipynb) presents the reconciled publication and reference
counts. [Performance](performance.ipynb) presents the cache-heavy rerun timings,
sampled process RSS, cache-directory disk measurements and final S2 output size.
Figures and tables are generated from the reporting data during compilation.
