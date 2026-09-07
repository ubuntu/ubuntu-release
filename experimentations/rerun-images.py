#!/usr/bin/python3
#
# Interactive rerun of image builds in the 'cdimage.ubuntu.com' Test Observer
# environment, for a given series.
#
# Usage:
#   ./rerun-images.py --series resolute
#
# Lists the image artefacts of the series, annotating each with the status of
# its latest 'Image build' test execution in the cdimage.ubuntu.com
# environment, then prompts to include/exclude images before triggering the
# rerun via POST /v1/test-executions/reruns.
#
# The trigger needs authentication; set TEST_OBSERVER_TOKEN (or pass --token) when
# your session API token is not picked up otherwise.

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://tests-api.ubuntu.com"
ENVIRONMENT = "cdimage.ubuntu.com"


def api(path, params=None, method="GET", body=None, token=None):
    """Thin urllib wrapper: handles JSON encoding and raises on errors."""
    url = BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise SystemExit(f"HTTP {error.code} for {method} {url}\n{detail}") from None


def get_artefacts(series, token):
    """All image artefacts of the series, sorted by os then name."""
    artefacts = api("/v1/artefacts", params={"family": "image"}, token=token)
    images = [a for a in artefacts if a.get("release") == series]
    images.sort(key=lambda a: (a["os"], a["name"]))
    return images


def get_latest_status(images, token):
    """
    Maps (name, version) to the status of the latest cdimage.ubuntu.com test
    execution of that image. Uses one batched search over the image names and
    falls back to a per-name probe when an image is missing from the page.
    """
    names = list(OrderedDict((a["name"], None) for a in images))
    executions = api(
        "/v1/test-executions",
        params={
            "families": "image",
            "environments": ENVIRONMENT,
            "artefacts": names,
            "limit": 500,
        },
        token=token,
    )["test_executions"]

    statuses = {}
    for execution in executions:
        artefact = execution["artefact"]
        key = (artefact["id"], artefact["name"], artefact["version"])
        current = statuses.get(key)
        if current is None or execution["id"] > current["id"]:
            statuses[key] = {
                "id": execution["id"],
                "status": execution["status"],
                "is_rerun_requested": execution["is_rerun_requested"],
            }

    def probe(name):
        page = api(
            "/v1/test-executions",
            params={
                "families": "image",
                "environments": ENVIRONMENT,
                "artefacts": name,
                "limit": 1,
            },
            token=token,
        )["test_executions"]
        if not page:
            return None
        execution = page[0]
        return (
            execution["artefact"]["id"],
            execution["artefact"]["name"],
            execution["artefact"]["version"],
        ), (
            execution["id"],
            execution["status"],
            execution["is_rerun_requested"],
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            index: pool.submit(probe, artefact["name"])
            for index, artefact in enumerate(images)
            if (artefact["id"], artefact["name"], artefact["version"]) not in statuses
        }
        for index, future in futures.items():
            result = future.result()
            if result is None:
                continue
            key, info = result
            artefact = images[index]
            if key == (artefact["id"], artefact["name"], artefact["version"]):
                statuses[key] = {
                    "id": info[0],
                    "status": info[1],
                    "is_rerun_requested": info[2],
                }

    return {
        (a["id"], a["name"], a["version"]): statuses.get(
            (a["id"], a["name"], a["version"])
        )
        for a in images
    }


def render_item(item):
    artefact = item["artefact"]
    info = item["info"]
    if info is None:
        status = "?"
        label = "not-seen"
    else:
        status = info["status"]
        label = status + ("*" if info["is_rerun_requested"] else "")
    return (
        f"{item['index']:>3} "
        f"{'[x]' if item['selected'] else '[ ]'} "
        f"{label:<27} "
        f"{artefact['os']:<27} "
        f"{artefact['name']:<50} "
        f"{artefact['version']:<10}"
    )


def is_non_passing(info):
    return info is not None and info["status"] != "PASSED"


def print_items(items):
    print(f"{' ':3} {'':3} {'cdimage status':<27} {'os':<27} {'name':<50} version")
    for item in items:
        print(render_item(item))
    selected = sum(1 for i in items if i["selected"])
    print(f"({selected}/{len(items)} selected)")


def prompt_loop(items, token):
    while True:
        print(
            "Commands: <number> toggle image, a=all, n=none, "
            "r=reset to failing, p=proceed, q=quit"
        )
        print()
        command = input("> ").strip().lower()
        if command == "q":
            print("Nothing triggered. Goodbye.")
            return False
        if command == "a":
            for item in items:
                item["selected"] = True
        elif command == "n":
            for item in items:
                item["selected"] = False
        elif command == "r":
            for item in items:
                item["selected"] = is_non_passing(item["info"])
        elif command == "p":
            selected = [i for i in items if i["selected"]]
            if not selected:
                print("No images selected.")
                continue
            print()
            print("Will request a rerun for the following images:")
            for item in selected:
                print(f"  {render_item(item)}")
            confirm = (
                input(
                    f"Trigger rerun in '{ENVIRONMENT}' for {len(selected)} "
                    f"image(s)? (y/N) "
                )
                .strip()
                .lower()
            )
            if confirm == "y":
                return selected
            print("Aborted.")
            continue
        else:
            try:
                index = int(command)
                item = next(i for i in items if i["index"] == index)
                item["selected"] = not item["selected"]
            except (ValueError, StopIteration):
                continue
        print()
        print_items(items)
        print()
    return None


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--series",
        "-s",
        type=str,
        required=True,
        help="The series to rerun images for (e.g. 'noble', 'resolute')",
    )
    parser.add_argument(
        "--token",
        "-t",
        type=str,
        default=None,
        help="Test Observer API token (defaults to the $TEST_OBSERVER_TOKEN env var)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    token = args.token or os.getenv("TEST_OBSERVER_TOKEN")

    print(f"Fetching {args.series} images from {BASE_URL}...")
    images = get_artefacts(args.series, token)
    if not images:
        raise SystemExit(f"No image artefacts found for series '{args.series}'.")

    statuses = get_latest_status(images, token)

    items = [
        {
            "index": index,
            "artefact": artefact,
            "info": statuses[(artefact["id"], artefact["name"], artefact["version"])],
            "selected": is_non_passing(
                statuses[(artefact["id"], artefact["name"], artefact["version"])]
            ),
        }
        for index, artefact in enumerate(images, start=1)
    ]

    print(f"\n Images of {args.series} tested in '{ENVIRONMENT}' ".center(110, "="))
    print_items(items)

    selected = prompt_loop(items, token)
    if not selected:
        return

    selected_with_ids = [item for item in selected if item["info"] is not None]
    if not selected_with_ids:
        raise SystemExit("No selected image has a recorded test execution to rerun.")
    skipped = [item for item in selected if item["info"] is None]
    if skipped:
        print(
            f"Skipping {len(skipped)} selected image(s) with no recorded "
            f"test execution: {', '.join(item['artefact']['name'] for item in skipped)}"
        )
    names = list(
        OrderedDict((item["artefact"]["name"], None) for item in selected_with_ids)
    )
    execution_ids = [item["info"]["id"] for item in selected_with_ids]
    print()
    print(f"Requesting rerun for {len(names)} image(s)...")

    print(f"""
    curl command:
    curl -v -X 'POST' \
        '{BASE_URL}/v1/test-executions/reruns?silent=true' \
        -H 'accept: application/json' \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer {token}' \
        -d '{
        json.dumps(
            {
                "test_execution_ids": execution_ids,
            }
        )
    }'
          """)
    # result = api(
    #     "/v1/test-executions/reruns",
    #     params={"silent": True},
    #     method="POST",
    #     body={"test_execution_ids": execution_ids},
    #     token=token,
    # )
    # print(f"Rerun request accepted for: {', '.join(names)}")
    # if result:
    #     print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
