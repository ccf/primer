# Publishing Primer to PyPI

The PyPI project is `useprimer` (matches the domain); the Python module is
still `primer`. Users install with `pip install useprimer` and invoke with
`primer ...`.

## One-time setup

1. Create a PyPI account at https://pypi.org and enable 2FA.
2. Go to https://pypi.org/manage/account/token/ and create an **API token**
   scoped to the `useprimer` project (first release can use an "Entire
   account" token, then narrow after upload).
3. Store the token in `~/.pypirc` or export as `TWINE_PASSWORD` at release
   time. Never commit it.

```ini
# ~/.pypirc
[pypi]
username = __token__
password = pypi-XXXXXXXXXXXXXX
```

## Release workflow

```bash
# 1. Bump version in pyproject.toml (e.g. 0.2.0 → 0.2.1)
$EDITOR pyproject.toml

# 2. Clean + build wheel and sdist
rm -rf dist build *.egg-info
python -m build              # produces dist/useprimer-X.Y.Z-py3-none-any.whl
                             #        + dist/useprimer-X.Y.Z.tar.gz

# 3. Sanity check
python -m zipfile -l dist/useprimer-*.whl | head -20
python -m twine check dist/*

# 4. Upload to TestPyPI first (strongly recommended)
python -m twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ useprimer

# 5. Upload to PyPI
python -m twine upload dist/*

# 6. Tag and push
git tag -a vX.Y.Z -m "vX.Y.Z"
git push --tags
```

## Verify after upload

- https://pypi.org/project/useprimer/ — project page renders README correctly
- Project-URL links all clickable (Homepage, Docs, Repo, Issues, Demo)
- `pip install useprimer` in a clean venv → `primer --version` works

## Why this matters beyond distribution

PyPI surfaces the six `[project.urls]` entries as inbound links from
pypi.org — a very high-authority domain Google trusts. That's an
SEO signal for `useprimer.dev` in addition to the developer-distribution
benefit.
