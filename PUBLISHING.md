# Publishing Primer to PyPI

The PyPI project is `useprimer` (matches the domain). The Python module is
still `primer`. Users install with `pip install useprimer` and invoke with
`primer ...`.

Releases are **published by CI on tag push**, not from a developer's laptop.
PyPI authenticates the workflow via OIDC trusted publishing, so there are
no PyPI tokens stored as repo secrets and nothing to rotate on developer
machines.

## One-time setup

### 1. PyPI trusted publishers

For both **PyPI** and **TestPyPI**, register the publisher under
`Account → Publishing`:

| Field | Value |
|------|-------|
| PyPI project name | `useprimer` |
| GitHub owner | `ccf` |
| Repository | `primer` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` (or `testpypi` on TestPyPI) |

PyPI: <https://pypi.org/manage/account/publishing/>
TestPyPI: <https://test.pypi.org/manage/account/publishing/>

### 2. GitHub environments

In this repo: **Settings → Environments → New environment** for both:

- `pypi` — recommend adding "Required reviewers" so a human approves prod releases.
- `testpypi` — no protection rules needed.

### 3. Initial PyPI registration

PyPI needs the project name reserved before trusted publishing works.
The first ever upload **must** happen with a project-scoped token to claim
`useprimer`. After that, switch to trusted publishing and never touch
tokens again.

```bash
python -m pip install --upgrade build twine
python -m build
# Generate a one-time API token at https://pypi.org/manage/account/token/
# scoped to "Entire account" (you can scope to useprimer after first upload).
TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-XXXX \
  python -m twine upload dist/*
# Then revoke or scope the token.
```

After this initial upload, all subsequent releases are CI-driven (below).

## Cutting a release

```bash
# 1. Bump the version in pyproject.toml (e.g. 0.2.0 → 0.2.1)
$EDITOR pyproject.toml

# 2. Commit on a release branch and merge via PR
git checkout -b release/v0.2.1
git commit -am "chore: bump version to 0.2.1"
git push -u origin release/v0.2.1
gh pr create

# 3. After merging, tag the merged commit and push
git checkout main && git pull
git tag -a v0.2.1 -m "v0.2.1 — <one-line release note>"
git push --tags
```

The `Publish to PyPI` workflow then:

1. Builds `dist/useprimer-X.Y.Z-py3-none-any.whl` and the matching sdist.
2. Verifies the pyproject version matches the tag (fails fast if not).
3. Runs `twine check --strict`.
4. Publishes to TestPyPI in the `testpypi` environment.
5. Publishes to PyPI in the `pypi` environment (gated by reviewer approval
   if you enabled protection rules).

## Manual rehearsal

To rehearse without tagging, run the workflow via the UI:

```
Actions → Publish to PyPI → Run workflow → branch=main, target=testpypi
```

That uploads whatever the working tree of `main` builds to TestPyPI and
skips PyPI entirely.

## Verifying after release

- <https://pypi.org/project/useprimer/> — README renders, project URLs
  clickable (Homepage, Docs, Repo, Issues, Demo).
- In a clean venv:
  ```bash
  pip install useprimer
  primer --version   # should match the tag
  ```

## Why this matters beyond distribution

PyPI surfaces the `[project.urls]` entries as inbound links from pypi.org —
a high-trust domain Google uses to prioritize crawls. Each release is an
SEO signal for `useprimer.dev` in addition to the developer-distribution
benefit.
