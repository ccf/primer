# Changelog

All notable changes to Primer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Automated review findings tracker** — structured tracking of findings from automated PR review bots (BugBot/cursor[bot]). Extensible parser registry supports adding more sources (CodeRabbit, SonarQube, etc.).
  - `ReviewFinding` model with severity, status, file path, and deduplication via unique constraint on `(pull_request_id, external_id)`
  - BugBot comment parser extracting severity, title, description, file location from cursor[bot] PR comments
  - GitHub PR comment fetching from issue comments, review comments (inline on diff), and review bodies
  - Webhook and sync integration — findings are automatically parsed on PR events and during repository sync
  - Findings overview aggregation in quality metrics: total count, severity breakdown, fix rate, avg per PR, daily trend
  - `GET /api/v1/analytics/review-findings` endpoint with source, severity, and status filters
  - Findings overview section on the Quality dashboard page (KPI cards + severity breakdown bar)
  - Findings table with sortable columns, severity/status badges, and file path display
  - Findings overview in engineer profile Quality tab
  - 16 new tests covering parser, upsert, aggregation, and API endpoints
