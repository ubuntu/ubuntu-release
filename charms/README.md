# Ubuntu Release charms

Each folder each represent one charm, representing one component of the Ubuntu Release infrastructure.

## Testing locally

### Charm tests

The charm has unit, functional and integration tests. To run them, follow these steps:

```bash
# Unit tests
❯ make -C charms/worker unit

# List spread tests (for functional and integration tests)
❯ charmcraft test --list charms/
lxd:ubuntu-24.04:charms/worker/tests/spread/functional/temporal
lxd:ubuntu-24.04:charms/worker/tests/spread/functional/worker
lxd:ubuntu-24.04:charms/worker/tests/spread/integration/deploy-charm:juju_3_6
lxd:ubuntu-24.04:charms/worker/tests/spread/integration/ingress:juju_3_6

# Run a particular functional test
❯ charmcraft test lxd:ubuntu-24.04:charms/worker/tests/spread/functional/temporal

# Run a particular integration test
❯ charmcraft test lxd:ubuntu-24.04:charms/worker/tests/spread/integration/ingress:juju_3_6
```

**NOTE**: before the functional and integration tests can be run, the `ubuntu-release-worker`
binary needs to be built and placed in the charm direction:

```bash
go build -o charms/worker/ubuntu-release-worker ubuntu-release-worker/main.go
```

## Generating the charmhub token for the CI

```
charmcraft login --export=secrets.auth --charm=ubuntu-release-worker  --permission=package-manage --permission=package-view --ttl=$((3600*24*365))
cat secrets.auth | wl-copy
shred -u secrets.auth
```

Go to <https://github.com/ubuntu/ubuntu-release/settings/secrets/actions> and
update the `CHARMHUB_TOKEN` secret.
