# Milestone 1: Data Crawling

## Objective and Workflow

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

## Reading the Results

The results address three questions: how much of the assigned corpus was
collected, what the reference pool contains, and where execution time and
storage were spent. The methods pages explain the code responsible for those
results; the analysis connects numerical observations to their interpretation and counting units.

- A **publication** is a base arXiv ID. Its revisions are **versions**; a
  publication marked `ok` does not by itself prove that every version has TeX.
- A **reference occurrence** belongs to a citing publication. The same work
  cited by two publications contributes two relations.
- A **cache hit** reuses a saved reference list. A successful rerun status can
  therefore include results that were not fetched anew in that run.
- The five assigned ranges are groups of inputs, not independent repeated
  benchmark trials or a random sample of all arXiv.

## Report Structure

This milestone report includes:

- [arXiv Crawler Implementation](implementation.md): discovery, source extraction,
  request handling, checkpoints and recovery.
- [Semantic Scholar References](semantic_scholar.md): API requests, local records,
  cache, table construction and validation.
- [Statistics](statistics.ipynb): publication outcomes, reference coverage and
  validation warnings across five ranges.
- [Performance](performance.ipynb): recorded crawl/recovery time, checkpoint
  storage and cache-heavy Semantic Scholar measurements.

## Data Sources and Reproducible Figures

The arXiv results are transcribed from Hieu's technical document. Semantic
Scholar results use the five per-range metrics, crawl-record CSVs and validation
reports from **11 November 2026**, together with Dat's measured final output
sizes. The 25,000 Semantic Scholar records were reconciled against the metrics
and validation summaries on **12 November 2026**.

Notebook code reads `milestone1/data/reported_results.json` and generates the
charts, supporting tables, totals and ratios during book compilation. The
analysis retains each stage's counting units, cache state and measurement scope.
