# Contributing

## Development Setup

```bash
uv sync --all-extras --all-groups
```

## Checks

```bash
make check
```

## Dependency Policy

Runtime dependencies should use conservative ranges in `pyproject.toml`.

Development and CI dependencies are locked in `uv.lock`.

Do not pin transitive dependencies in published package metadata unless there is a known incompatibility.

## Tests

Unit tests should be deterministic and avoid live network calls.

Integration tests must be marked with `@pytest.mark.integration` and must be safe to skip in default CI.

## Releases

Use Conventional Commits. Release PRs and changelog updates are managed by release-please.
