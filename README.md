# Ubuntu Release

This repo hosts the tooling used to generate Ubuntu images hosted on the not yet
existing https://images.ubuntu.com.

**DISCLAIMER**: this is very early work, as we're trying to move away from a
very manual process and setup on https://cdimage.ubuntu.com. This repo is still
very much the future, and not everything is clearly defined yet. If you want
to submit feature requests, please make sure you already understand Ubuntu's
release mechanisms, and have a strong use-case in mind to show that it needs to
be taken into account early.

## ubuntu-release go binary

`ubuntu-release` is a Go utility to facilitate the Ubuntu Release activities.

### Quick start local run

To start the local Temporal server:

```bash
❯ temporal server start-dev
```

To start the Temporal worker:

```bash
❯ go run cmd/ubuntu-release-worker
```

To start the HelloUbuntu Temporal workflow:

```bash
❯ go run cmd/ubuntu-release hello
```

### Running Tests

The `ubuntu-release` project has both unit and integration tests. To run them:

```bash
# Unit tests
❯ go test ./...

# List integration tests
❯ spread -list ubuntu-release

# Run an integration test
❯ spread -v lxd:ubuntu-24.04:tests/hello
```

## Charm Test & Release

Charm code can be found in [charm](./charm).

### Charm tests

The charm has unit, functional and integration tests. To run them, follow these steps:

```bash
# Unit tests
❯ make -C charm unit

# List spread tests (for functional and integration tests)
❯ charmcraft test --list charm/
lxd:ubuntu-24.04:charm/tests/spread/functional/temporal
lxd:ubuntu-24.04:charm/tests/spread/functional/worker
lxd:ubuntu-24.04:charm/tests/spread/integration/deploy-charm:juju_3_6
lxd:ubuntu-24.04:charm/tests/spread/integration/ingress:juju_3_6

# Run a particular functional test
❯ charmcraft test lxd:ubuntu-24.04:charm/tests/spread/functional/temporal

# Run a particular integration test
❯ charmcraft test lxd:ubuntu-24.04:charm/tests/spread/integration/ingress:juju_3_6
```

### Generating the charmhub token for the CI

```bash
charmcraft login \
  --export=secrets.auth \
  --charm=ubuntu-release-worker \
  --permission=package-manage \
  --permission=package-view \
  --ttl=$((3600*24*365))
cat secrets.auth | wl-copy
shred -u secrets.auth
```

Go to <https://github.com/ubuntu/ubuntu-release/settings/secrets/actions> and
update the `CHARMHUB_TOKEN` secret.
