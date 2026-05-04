# Agent Instructions

- Use `uv` for dependency management, testing, and builds.
- Keep the PyPI distribution name as `polymarket-sdk` and the import package as `polymarket` unless explicitly changed.
- When implementing new areas where guidance is vague, choose the most idiomatic Python approach but avoid premature abstractions.
- Prefer simple, direct code until there is a concrete repeated use case or public API need that justifies a helper, wrapper, protocol, base class, or configuration abstraction.
- Do not copy TypeScript SDK shapes mechanically; preserve feature parity while adapting APIs to Python ecosystem norms and the smallest useful surface.
- The SDK should present one cohesive consumer interface and hide current service boundaries where possible.
- Design public APIs around developer workflows rather than the current split between underlying APIs.
- Do not mirror today's service fragmentation directly in the public SDK surface.
- Public docs and docstrings should describe the unified SDK behavior; avoid mentioning underlying service names unless the user specifically asks, a low-level escape hatch requires it, or a test needs to document a boundary.
- Lower-level controls are acceptable when they support a concrete integration need, but the default experience should feel unified.
- Do not add live trading tests to the default test suite.
- Mark live service tests with `@pytest.mark.integration`.
- During initial development, do not assume every merged change needs its own changelog entry or published release.
- Do not merge or generate a release PR until the SDK has a meaningful first beta surface and the user explicitly asks for release preparation.
- For the first published package, prefer one manually curated changelog entry for the initial beta release instead of listing every setup/early-development change.
- Use PEP 440 pre-release versions for beta/RC publishing, such as `0.1.0b1` or `0.1.0rc1`.
