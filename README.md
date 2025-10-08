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

## Quick start local run

To start the local Temporal server:

```bash
temporal server start-dev
```

To start the Temporal worker:

```bash
go run ubuntu-release-worker/main.go
```

To start the HelloUbuntu Temporal workflow:

```bash
go run ubuntu-release/main.go hello
```

## Running Tests

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

See [Charm README](charms/worker/README.md).
