# Ubuntu Release

This repo hosts the tooling used to generate Ubuntu images hosted on
https://images.ubuntu.com.

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
```
temporal server start-dev
```

To start the Temporal worker:
```
go run ubuntu-release-worker/main.go
```

To start the HelloUbuntu Temporal workflow:
```
go run ubuntu-release/main.go hello
```
