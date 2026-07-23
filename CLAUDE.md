# Claude Configuration for template_cli

This project follows [ownjoo-org](https://github.com/ownjoo-org) standards and guidelines.

## Key Standards

- **Simplicity First** — Write the simplest code that solves the problem. No premature optimization.
- **Integration Testing** — Prefer integration tests hitting real dependencies over mocks.
- **No Defensive Code** — Only validate at system boundaries (CLI input, API responses). Trust internal code.
- **Security by Default** — Never introduce command injection, XSS, SQL injection, or OWASP Top 10 vulnerabilities.
- **Explicit Commits** — Use conventional commits with clear messages and `Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>`.

## Code Quality

- **Type Hints** — All functions have type annotations. Run `mypy` to validate.
- **Linting** — Use `ruff` for linting and `black` for formatting.
- **Testing** — Use `unittest.IsolatedAsyncioTestCase` for async tests (no external dependencies).
- **Coverage** — Aim for >80% coverage on new code.

## Development Workflow

1. Create feature branch from `main`
2. Make focused commits following conventional commit format
3. Run quality checks: `make lint format type-check test`
4. Submit PR with clear description and testing approach
5. All CI checks must pass before merge

## Key Files

- **`CLAUDE.md`** — This file (organization standards)
- **`pyproject.toml`** — Project metadata, dependencies, tool configuration
- **`Makefile`** — Common development commands
- **`.github/workflows/ci.yml`** — Automated CI/CD pipeline

## Async Patterns

This project demonstrates async HTTP patterns using:

- **`httpx`** — Modern async HTTP client with HTTP/2 support
- **`asyncio.Queue`** — Coordinates concurrent tasks (producers/consumers)
- **`retry-async`** — Automatic retry with exponential backoff
- **`unittest.IsolatedAsyncioTestCase`** — Built-in async test support

See `template_cli/client.py` and `template_cli/main.py` for examples.

## Reusable Patterns

This project documents patterns useful for building CLI tools with async APIs:

- **Pagination with Result Limits** — See `PATTERNS.md` for configurable result limits with smart page-size optimization
- **Async Test Patterns** — See `TESTING.md` for unittest.IsolatedAsyncioTestCase examples and async testing strategies
- **HTTP Client Patterns** — Automatic retry with exponential backoff, basic authentication, proxy support
- **Concurrent Task Coordination** — Using asyncio.Queue for producer/consumer patterns

See `PATTERNS.md` and `TESTING.md` for comprehensive documentation and examples.

## Contributing

Before making changes:

1. Read this file (CLAUDE.md)
2. Follow the patterns documented in `PATTERNS.md` and `TESTING.md`
3. Ensure all tests pass: `python -m unittest discover test/`
4. Run quality checks: `make lint format type-check test`
5. Update this file if new standards should be documented
