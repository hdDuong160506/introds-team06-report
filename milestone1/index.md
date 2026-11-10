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
results; the analysis distinguishes observations from explanations that still
require logs.

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
  reported validation issues across five ranges.
- [Performance](performance.ipynb): recorded crawl/recovery time, checkpoint
  storage and cache-heavy Semantic Scholar measurements.

## Evidence and Pending Updates

The current report uses the supplied code snapshot and the updated technical
documents `Hieu.docx` and `Dat.docx`, reviewed on **9 November 2026**. Both
documents report five ranges of 5,000 input IDs. The presentation was revised
on **10 November 2026**; no new crawler results were supplied for this revision.
Numeric aggregates have been
transcribed into a small report data file; notebook code generates the figures
and supporting tables and recomputes totals and ratios during book compilation.
Statistics and performance are presented primarily through charts, with their
interpretation and measurement scope stated alongside each figure.

These are document-reported results. Original per-range metrics, runtime
ledgers, crawl records and validation exports have been requested for
reconciliation. The supplied notebooks contain no saved execution outputs, and
the crawler's offline test suites have not been run as part of preparing this
report.

> **Current scope: partial evidence.** The available aggregates support
> provisional publication/reference counts and separately scoped stage
> measurements. Full version coverage, paired before/after source sizes and an
> auditable full-system benchmark are still awaiting evidence. Missing values
> are identified explicitly and are not plotted as zero.

Pending items use stable labels throughout the results pages:

- **S1:** version coverage and source-status reasons.
- **S2:** average source size in bytes before and after filtering.
- **S3:** reference records, payload checks and metadata validation.
- **S4:** publication-level distributions, an additional analysis when records
  become available.
- **P1:** run configurations and original timing ledgers.
- **P2:** complete processing time, discovery time and per-publication timing.
- **P3:** RAM across the full M1 execution window.
- **P4:** peak disk and complete final M1 output size.

The [Statistics](statistics.ipynb) and [Performance](performance.ipynb) pages
state the data needed to close each item. This follows the
[M1 report requirements](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/crawling/);
recording a gap does not mean that the corresponding requirement has been met.
