# arXiv Crawler Implementation

## Overview

This section describes the arXiv crawler in the supplied
`arXir_project-main.zip` snapshot, together with Hieu's updated technical
document reviewed on 9 November 2026. It collects publication metadata and the source of
every identified version within the assigned ID ranges. Its outputs support
Milestone 2 and the subsequent integration of reference metadata.

The standalone entry point is `src/m1_crawling/run_arxiv_only.py`. It can run
independently of reference collection. The description below follows the
implemented functions in the reviewed snapshot. Document-reported results are presented in
[Statistics](statistics.ipynb) and [Performance](performance.ipynb). The underlying
run exports are pending reconciliation; implementation details alone do not
establish collection success or performance improvements.

## Processing Pipeline

```text
Select an assigned range
    -> Expand IDs and split into batches
    -> Discover metadata
    -> Enumerate versions
    -> Download and identify each version's source
    -> Extract .tex/.bib files
    -> Record statuses and metrics
    -> Package and save a checkpoint
```

Batches run sequentially. Within a batch, publications can be processed
sequentially or by multiple workers. Each publication's versions are processed
sequentially. Results are reordered to match the input IDs before being written,
regardless of worker completion order.

### Design Rationale

- Batched metadata lookup limits repeated API calls. Streaming and selective
  extraction limit the data held at once and retain the source files used by M2.
- Source bytes and relative paths are preserved so that later parsing can
  follow the original document structure. A version without retained sources
  still receives a record, keeping absence visible in coverage statistics.
- Checkpoints and targeted Recovery let work continue after interruptions.
  Their runtime/storage costs are measured separately in the available results;
  a claimed speedup would require a comparable experiment.

> **Pending evidence S1 and P1.** The method enumerates versions, but final
> version counts, source-status reasons and the actual configurations behind
> the reported runs still need the owners' exports. The discussion below
> describes the reviewed snapshot, including limitations that have not yet been
> confirmed as corrected.

## Assigned IDs and Batching

`assigned_ranges.py` stores each range's first ID, last ID and, where needed,
`cross_month_limit`. `range_ids()` validates the modern ID format, month and
endpoint order, then expands either a single month or two consecutive months.
`assigned_ids()` selects one range or all five and checks for duplicate IDs.

For a cross-month range, expansion continues to the configured end of the first
month and resumes at serial `00001` in the next month. The monthly numbering
scheme is documented by [arXiv](https://info.arxiv.org/help/arxiv_identifier.html).
The configured boundary must be verified; arithmetic expansion does not prove
that an ID exists. In particular, the implementation does not assume that every
assigned range contains a fixed number of valid publications.

The optional `--verify-boundaries` check queries each configured month-end ID
and its successor. It stops the run if the former is absent or the latter is
present. This is a boundary consistency check, not proof of the existence of
every ID in the range, and it is not enabled automatically.

`build_batches()` partitions the list into stable names such as `batch_00000`.
The default checkpoint batch size is **50 IDs**; the CLI accepts **1--100**.
Resuming in the same checkpoint directory requires the same batch size, selected
range and ID ordering. Changing the worker count does not change batch membership.

## Metadata Discovery and Version Resolution

### Batched Atom API lookup

`fetch_papers_by_ids()` in `discover.py` queries
`https://export.arxiv.org/api/query` directly through the HTTP client. It accepts
at most 100 IDs per request. The following excerpt shows the lookup parameters:

```python
with http.get(API_URL, params={"id_list": ",".join(arxiv_ids),
                               "start": 0, "max_results": len(arxiv_ids)}) as response:
    parsed = _parse_feed(response.content)
```

Combining IDs reduces the number of metadata calls compared with requesting
each publication separately. An API lookup batch and a checkpoint batch are
different concepts, even when one lookup covers an entire checkpoint batch.

`_parse_feed()` uses `xml.etree.ElementTree` to read Atom entries. It normalizes
whitespace in titles and author names and creates `PaperMeta` objects containing
the base ID, title, authors, abstract, categories, latest version, submission
date, revision dates, venue and supplementary `raw` fields. Dates are stored as
`YYYY-MM-DD` strings. Explanatory API error entries and entries that cannot be
parsed as valid publication metadata are skipped.

HTTP/API failures raise an exception. The coordinator records unresolved
publications as discovery errors in that case instead of treating the entire
failed request as evidence that those publications do not exist.

### Enumerating all versions

The parser separates the base ID and version suffix from each returned
identifier. `list_versions()` expands the latest version number into the
versions that the source downloader must attempt:

```python
def list_versions(meta: PaperMeta) -> list[int]:
    if meta.latest_version < 1:
        raise ValueError("Invalid latest_version")
    return list(range(1, meta.latest_version + 1))
```

For `latest_version=3`, the result is `[1, 2, 3]`. A publication with one version
is still downloaded using the explicit suffix `v1`. Enumerating a version is
distinct from successfully retrieving its source; the latter is recorded separately.

### Revision dates and metadata scope

The initial lookup supplies the submission date and latest update date.
`_enrich_revision_dates()` additionally requests intermediate versions
`v2` through `v(N-1)` in groups of up to 80 versioned IDs. No intermediate lookup
is needed for a publication with only one or two versions.

The local `raw` metadata includes `revision_dates_complete` and, where available,
`intermediate_version_dates`. Missing intermediate dates or a failed enrichment
request are not presented as a complete history. The `--no-version-dates` option
skips enrichment. Recovery can reuse saved metadata rather than querying it again.

Titles and authors come from the latest publication metadata. Per-version
`metadata.json` therefore uses `title_latest`, `authors_latest` and
`title_authors_scope="latest_publication_only"`. These fields are not historical
titles or author lists independently retrieved for every revision.

## Source Download and Extraction

### Version-specific streaming downloads

`source_url()` constructs a separate URL for every version:

```text
https://export.arxiv.org/src/{arxiv_id}v{version}
```

The downloader supports modern assigned IDs. `download_source_archive()` streams
the response in **256 KiB** chunks to avoid holding the whole archive in memory:

```python
for chunk in response.iter_content(chunk_size=256 * 1024):
    if chunk:
        count += len(chunk)
        if count > max_bytes:
            raise ValueError(f"Archive exceeds {max_bytes} bytes")
        out.write(chunk)
```

Downloads are first written to a `.partial` file and renamed after completion.
An exception removes the partial download. Temporary source archives are deleted
after the version has been processed.

### Source format detection

`detect_archive_kind()` inspects content rather than trusting a filename suffix.
It distinguishes gzipped tar, tar, ZIP, single gzip, standalone TeX, PDF, empty
responses and unknown content. Standalone TeX is saved as `main.tex`. For a
single gzip, the decompressed prefix is checked before saving it as TeX.

Unknown content raises an extraction error instead of being automatically
classified as PDF-only. This is conservative format recognition, not a full
validation of LaTeX syntax or successful document compilation.

### Selective extraction and resource limits

`extract_tex_and_bib()` keeps only files with `.tex` or `.bib` suffixes. It
preserves their bytes and relative paths, allowing M2 to resolve `\input` and
`\include`. Image binaries are excluded, while LaTeX `figure` environments and
`\includegraphics` commands remain unchanged.

The extractor rejects unsafe relative paths, skips symbolic links and limits
archive processing. The configured limits are:

- Downloaded archive: **400 MiB**.
- Individual extracted file: **64 MiB** in the latest supplied code (32 MiB in
  the earlier snapshot).
- Total extracted content per source archive: **120 MiB**.
- Archive members examined: at most **5,000**.

These are protective configuration thresholds, not measured corpus sizes. A
limit violation is recorded as a processing error, not a successful extraction.

## HTTP Scheduling and Error Handling

### Shared scheduling and retries

`ArxivHTTP` manages requests, retry counters and shared cooldown state. Each
thread has its own `requests.Session`. The CLI defaults to a **3.1-second**
scheduling interval and rejects a configured interval below **3 seconds**.
Connection timeout is **15 seconds** and the default read timeout is **90 seconds**.
The updated `_pace()` rechecks the monotonic deadline after sleeping, accounting
for clock granularity rather than assuming that one sleep reaches the deadline.

The client retries network exceptions during request establishment and HTTP
`429`, `500`, `502`, `503` and `504`. It uses increasing waits and parses
`Retry-After` when present. The current HTTP-status backoff calculation caps the
wait at 120 seconds, so a larger server-provided delay is not fully preserved.
Network-exception backoff is capped at 90 seconds. A shared cooldown postpones
subsequent scheduling across workers.

Errors while consuming a streamed response can propagate to the publication
handler and require a later recovery run; they are not necessarily retried
within the same download attempt.

The CLI defaults to four retries after the initial attempt. The supplied Colab
Fast Crawl wrapper overrides this with `--retries 0`; the example Recovery call
uses one retry. The actual run configuration must accompany benchmark results.

### Concurrent mode and connection limits

The CLI defaults to one worker. The supplied concurrent notebook sets
`MAX_WORKERS=3`. `ThreadPoolExecutor` parallelizes publications inside a batch,
while the coordinator alone writes the batch-level outputs.

The shared lock covers scheduling and counters, not the wait for a response or
stream consumption. Multiple connections can therefore overlap. Request
scheduling intervals must not be described as a guarantee of a single active
connection. The [arXiv API terms](https://info.arxiv.org/help/api/tou.html) also
require a single connection for legacy API access; the concurrent configuration
must be reviewed against that restriction before claiming full compliance.
The supplied notebooks use three workers, while the document describes a
single active connection. The actual worker configuration behind each reported
run is pending confirmation. No measured concurrent speedup is established.

Although the help text describes 1--4 workers, the CLI validation currently
checks only that the number is positive. Four is not an enforced upper bound.

### Publication and version statuses

Each version records `status`, `reason`, `archive_kind`, downloaded and retained
bytes, file count, relative file paths and elapsed time. In the supplied code:

- `ok`: at least one `.tex` or `.bib` file was extracted.
- `no_tex`: PDF, empty content, no retained source files, or a source HTTP 404/410.
- `error`: an unresolved technical failure, including unrecognized content or an
  extraction error.
- `not_found`: a publication-level result when discovery yields no usable
  metadata without a discovery exception.

Paper status is aggregated from its version statuses:

```text
Any version is error                     -> paper is error
No errors and at least one version is ok -> paper is ok
Otherwise                               -> paper is no_tex
```

A paper marked `error` can still have successfully downloaded versions.
Metadata is retained when source retrieval fails. Versions classified as
`no_tex` receive an `empty.json` record containing the reason.

There are interpretation limits: an archive containing only `.bib` can be `ok`,
and a source 404/410 does not by itself prove that LaTeX never existed.
Likewise, `not_found` means no usable entry was returned at lookup time, since
the parser also skips malformed entries. These statuses must be inspected with
their reasons when computing coverage; source success and metadata discovery
success are separate measurements.

## Checkpoints, Resume and Recovery

### Persistent batch storage

Each checkpoint consists of `batch_XXXXX.tar.gz` and an external
`batch_XXXXX.json` manifest. The logical contents of a generated archive are:

```text
papers.jsonl
crawl_records.jsonl
metrics.json
working/
  <publication-key>/
    paper.json
    status.json
    v<version>/
      metadata.json
      status.json
      sources/       # retained files when available
      empty.json     # present for no_tex versions
```

The crawler writes an archive to a temporary path, calculates SHA-256, renames
the completed archive, then writes the manifest as a completion marker. The
manifest records IDs, status counts, archive size and checksum. After a
successful checkpoint save, the batch scratch directory is removed.

Resume checks require both files, the expected ID list and a matching archive
size. Recomputing SHA-256 is optional through `--check-backups`; it is not
performed automatically on every resume.

### Fast Crawl and targeted Recovery

Fast Crawl processes batches without a valid checkpoint. A checkpoint can be
complete as a saved batch while still containing failed publications; Fast
Crawl skips it until Recovery is requested.

Recovery (`--retry-failed`) selects existing valid checkpoints with errors and
does not create new batches. It restores the checkpoint, reuses saved metadata
and retries failed publications. Within those publications it preserves
`ok` and `no_tex` versions, checking the recorded files exist before reusing an
`ok` version. Failed or missing versions are downloaded again.

Existing `not_found` and `no_tex` records are not automatically retried as
network failures. Their classification therefore matters for subsequent
coverage. A batch interrupted before checkpoint completion can require another
run. Only one process or notebook should write to a checkpoint directory at a time.

## Output Data and Consistency Checks

### Publication metadata and crawl records

`papers.jsonl` contains a row for each publication with saved metadata,
including publications whose sources fail or are classified as `no_tex`. Its
fields are:

- `arxiv_id`: base publication ID, string.
- `title`: latest publication title, string.
- `authors`: list of author names.
- `submission_date`: date string.
- `revised_dates`: list of available revision date strings; inspect the richer
  local metadata to determine whether the history is complete.
- `venue`: journal reference when present, otherwise null.

`crawl_records.jsonl` stores one record per requested ID, with publication
status and nested version records. These are internal working records, not a
claim that final flat dataset export and full M1 validation are complete.

### Report export and validation

`export_reports.py` reads checkpoint metadata without extracting all sources
and writes `papers.csv`, `crawl_records.csv`, `metrics.csv`,
`failed_versions.csv`, `issues_explained_vi.csv`, `runtime_history.csv`,
`summary.json` and a reading guide.

It checks the completion marker, archive size, IDs against the manifest,
duplicate record IDs and overlaps between batches. SHA-256 checking is optional
through `--verify-sha256`. These checks establish checkpoint consistency, not
the correctness of every bibliographic field or successful parsing in M2.

Version-level analysis must use `crawl_records`, not only the issue export:
the current issue exporter skips papers whose aggregate status is `ok`, so a
`no_tex` version inside an otherwise successful paper can be absent from that
issue list.

## Runtime and Resource Measurement

`ResourceSampler` samples the crawler process RSS approximately every second
and scratch-directory size approximately every five seconds. Batch metrics also
record discovery duration, request/retry counts, downloaded archive bytes and
retained source bytes. Sampling ends before checkpoint packaging, so these
values do not include the complete backup stage or total Drive usage.

The Colab wrapper separately measures the crawler subprocess wall time and
records each Fast Crawl or Recovery event in `runtime_history.csv` through
`runtime_tracking.py`. The ledger is read when exporting; repeated exports do
not add runtime. Historical runs before ledger recording and sessions stopped
before an event was saved cannot be reconstructed automatically.

For interpretation:

- `metrics.csv` describes the latest execution of each saved batch, not
  cumulative Fast Crawl plus Recovery history.
- Cumulative recorded wall time comes from the ledger, not the sum of worker
  durations or latest checkpoint runtimes.
- `average_seconds_per_id` divides recorded wall time by the number of current
  crawl records, which can include `not_found`; its denominator must be stated.
- Sampled maxima can miss short RAM or disk peaks.
- `archive_bytes` is downloaded archive size, while `filtered_bytes` is the
  uncompressed size of retained files; their ratio is not an equal-compression
  comparison of storage reduction.

The [Performance](performance.ipynb) page includes the time and checkpoint sizes
reported in the updated document, with their measurement scope and rounding
discrepancies. RAM, discovery time, version coverage and equal-basis source-size
comparisons remain pending where no results were supplied. Final M1 benchmarking must additionally cover
the reference crawler and other integration steps on Google Colab CPU-only, as
specified in the [milestone requirements](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/crawling/).

## Tools and Libraries

The implemented arXiv path uses Python, `requests` for HTTP and streaming,
`xml.etree.ElementTree` for Atom XML, `tarfile`/`gzip`/`zipfile` for sources,
`concurrent.futures`/`threading` for workers and scheduling, `hashlib` for
checksums, and `psutil`/`time` for measurements. Google Colab runs the supplied
notebook and Google Drive stores persistent checkpoints.

The crawler dependency file specifies `requests>=2.31,<3`, `psutil>=5.9,<8` and
`pytest>=8,<10`. These are allowed dependency ranges, not a record of package
versions installed during a benchmark. The actual arXiv path calls the API
directly; it does not use `arxiv.py`, OAI-PMH or Kaggle.

The ZIP includes offline tests for crawler behavior, concurrency and runtime
tracking. They have been inspected for this description but not executed as
part of preparing this report. No test-pass count or live crawl validation is
claimed here.

## Semantic Scholar Reference Collection

The arXiv metadata checkpoints feed the separate
[Semantic Scholar crawler](semantic_scholar.md). Its reference collection,
normalization, cache behavior, table construction and current limitations are
described on that page. Combined document-reported results are available in
[Statistics](statistics.ipynb) and [Performance](performance.ipynb).
