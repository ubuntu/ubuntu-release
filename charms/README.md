# Ubuntu Release charms

Each folder each represent one charm, representing one component of the Ubuntu Release infrastructure.

## Testing locally

In each folder, one can get the integration tests running by using the following commands:
* `charmcraft pack`
  This will pack the charm in its own folder. The tests have some magic fixtures
  to find the right `.charm` files to use in the tests.
* `uv run pytest tests/ -vv --log-level=INFO -o log_cli=1`
  This is for maximum live verbosity. You don't actually need all those flags to
  just run the tests, but I find that convenient in development.

