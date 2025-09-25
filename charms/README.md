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

NOTE: for the `worker` charm, you'll need an `ubuntu-release-worker` binary to
sit next to `charmcraft.yaml`. This can be generated once with:
```
go build -o ubuntu-release-worker ../../ubuntu-release-worker/main.go
```

## Generating the charmhub token for the CI

```
charmcraft login --export=secrets.auth --charm=ubuntu-release-worker  --permission=package-manage --permission=package-view --ttl=$((3600*24*365))
cat secrets.auth | wl-copy
shred -u secrets.auth
```

Go to <https://github.com/ubuntu/ubuntu-release/settings/secrets/actions> and
update the `CHARMHUB_TOKEN` secret.
