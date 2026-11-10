# Milestone 1: Data Crawling

## Objective

Milestone 1 focuses on collecting paper metadata, source files,
and reference metadata from arXiv and Semantic Scholar.

The arXiv stage identifies assigned publications and their versions, downloads
the sources, retains `.tex`/`.bib`, and writes resumable checkpoints. The
Semantic Scholar stage reads publication metadata from those checkpoints and
retrieves the references cited by each publication. Matching references against
BibTeX entries is a later milestone.

```text
Assigned arXiv IDs
    -> arXiv metadata + versioned .tex/.bib sources + checkpoints
    -> Semantic Scholar reference metadata + per-publication cache
    -> papers / references working tables + validation and measurements
```

A publication is identified by its base arXiv ID; `v1`, `v2`, and subsequent
revisions are versions of that publication. References are associated with the
citing publication's base ID. The cited publication may be outside the group's
assigned ranges.

## Report Structure

This milestone report includes:

- [arXiv Crawler Implementation](implementation.md): discovery, source extraction,
  request handling, checkpoints and recovery.
- [Semantic Scholar References](semantic_scholar.md): API requests, local records,
  cache, table construction and validation.
- [Statistics](statistics.ipynb): publication outcomes, reference coverage and
  reported validation issues across five ranges.
- [Performance](performance.ipynb): recorded crawl/recovery time, checkpoint
  storage and cache-heavy Semantic Scholar measurements.

## Evidence and Current Scope

The current report uses the supplied code snapshot and the updated technical
documents `Hieu.docx` and `Dat.docx`, reviewed on **9 November 2026**. Both
documents report five ranges of 5,000 input IDs. Numeric aggregates have been
transcribed into a small report data file; notebook code generates the figures
and supporting tables and recomputes totals and ratios during book compilation.
Statistics and performance are presented primarily through charts, with their
interpretation and measurement scope stated alongside each figure.

These are document-reported results. Original per-range metrics, runtime
ledgers, crawl records and validation exports have been requested for
reconciliation. The supplied notebooks contain no saved execution outputs, and
the crawler's offline test suites have not been run as part of preparing this
report. Pending details are stated alongside the relevant methods and results.
