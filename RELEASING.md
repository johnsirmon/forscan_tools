# Release Process

This document is the single authoritative guide for publishing a new version of `forscan-tools`.
Follow every step in order; each command is copy/paste-ready.

---

## Semantic Versioning Policy

This project follows [Semantic Versioning 2.0.0](https://semver.org/) (`MAJOR.MINOR.PATCH`):

| Segment | Increment when… |
|---------|----------------|
| `MAJOR` | A public interface changes in a backwards-incompatible way (e.g. removed CLI flag, changed output schema). |
| `MINOR` | New functionality is added in a backwards-compatible way (e.g. new subcommand, new output field). |
| `PATCH` | Backwards-compatible bug fixes or documentation updates only. |

> While the project is at `0.x.y`, minor-version bumps may include breaking changes.
> Stabilise the public interface before tagging `1.0.0`.

---

## Pre-release Checklist

### 1. Verify you are on a clean `main` branch

```bash
git checkout main
git pull origin main
git status          # must show "nothing to commit, working tree clean"
```

### 2. Bump the version in `pyproject.toml`

Open `pyproject.toml` and edit the `version` field:

```toml
[project]
version = "X.Y.Z"   # e.g. "0.3.0"
```

Commit the change:

```bash
git add pyproject.toml
git commit -m "chore: bump version to X.Y.Z"
```

### 3. Run local quality gates

All commands must exit with code `0` before proceeding.

```bash
# Install dev dependencies if not already present
pip install -e .[dev]

# Unit tests
pytest

# Linter
ruff check .

# Formatter check (no auto-fix)
ruff format --check .

# Build source distribution and wheel
python -m build

# Validate the distributions
twine check dist/*
```

> **Tip:** clean the `dist/` directory before building to avoid checking stale artifacts:
> ```bash
> rm -rf dist/
> python -m build
> twine check dist/*
> ```

### 4. Tag the release

Tags must follow the format `vX.Y.Z` (the `v` prefix is required).

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main --follow-tags
```

---

## GitHub Release

### 5. Create the release on GitHub

1. Go to **[Releases → Draft a new release](https://github.com/johnsirmon/forscan_tools/releases/new)**.
2. Select the tag `vX.Y.Z` created above.
3. Set the **release title** to `vX.Y.Z`.
4. Paste release notes into the description (see template below).
5. Attach the files from `dist/` (`*.tar.gz` and `*.whl`) as binary assets.
6. Click **Publish release**.

### Release Notes Template

```
## What's Changed

### Added
- 

### Changed
- 

### Fixed
- 

### Removed
- 

**Full Changelog**: https://github.com/johnsirmon/forscan_tools/compare/vPREV...vX.Y.Z
```

---

## Post-release

### 6. Verify the published release

```bash
pip install forscan-tools==X.Y.Z
pip show forscan-tools          # confirm version field matches X.Y.Z
```

### 7. Open the next development cycle (optional)

Bump the version to the next anticipated release with a `.dev0` suffix to make it clear that
`main` is ahead of the published release:

```bash
# Edit pyproject.toml: version = "X.Y+1.0.dev0"
git add pyproject.toml
git commit -m "chore: begin X.Y+1.0 development"
git push origin main
```

---

## Quick Reference

| Step | Command |
|------|---------|
| Install dev deps | `pip install -e .[dev]` |
| Run tests | `pytest` |
| Lint | `ruff check .` |
| Format check | `ruff format --check .` |
| Build | `python -m build` |
| Validate build | `twine check dist/*` |
| Tag | `git tag -a vX.Y.Z -m "Release vX.Y.Z"` |
| Push with tag | `git push origin main --follow-tags` |
