"""Launchpad API interactions for the upload queue."""

from __future__ import annotations

import subprocess
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# Default Ubuntu series to operate on.
DEFAULT_SERIES = "resolute"

# Launchpad queue status strings expected by the API.
QUEUE_STATUS_NEW = "New"
QUEUE_STATUS_UNAPPROVED = "Unapproved"
QUEUE_STATUS_ACCEPTED = "Accepted"
QUEUE_STATUS_DONE = "Done"
QUEUE_STATUS_REJECTED = "Rejected"

# All queue statuses in display order.
QUEUE_STATUSES = [
    QUEUE_STATUS_NEW,
    QUEUE_STATUS_UNAPPROVED,
    QUEUE_STATUS_ACCEPTED,
    QUEUE_STATUS_DONE,
    QUEUE_STATUS_REJECTED,
]


@dataclass
class QueueItem:
    """Represents a single item in the upload queue."""

    source_name: str
    version: str
    component: str
    section: str
    archive_url: str
    date_created: str
    status: str
    is_sync: bool
    changes_file_url: str | None
    authors: str = ""
    lp_item: object | None = None

    @property
    def display_name(self) -> str:
        """Return a display-friendly name for the item."""
        return f"{self.source_name}/{self.version}"


class LaunchpadQueue:
    """Interface to the Launchpad upload queue."""

    def __init__(self, series: str = DEFAULT_SERIES):
        self.series = series
        self._lp = None
        self._ubuntu = None
        self._archive = None
        self._series = None
        self._debian_archive = None
        self._log_callback: Callable[[str], None] | None = None
        self.work_dir = Path().home() / "lp-queue"
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback to receive debug log messages.

        Args:
            callback: A callable that accepts a single log-message string.
        """
        self._log_callback = callback

    def _log(self, message: str) -> None:
        """Send *message* to the registered log callback (if any)."""
        if self._log_callback is not None:
            self._log_callback(message)

    def connect(self) -> None:
        """Authenticate and connect to Launchpad.

        Uses launchpadlib to obtain OAuth credentials and connect
        to the production Launchpad instance.  The first run will open a
        browser window for OAuth authorization; subsequent runs reuse the
        stored credentials.
        """
        from launchpadlib.launchpad import Launchpad

        self._lp = Launchpad.login_with(
            "lp-queue-tui",
            "production",
            version="devel",
        )
        self._ubuntu = self._lp.distributions["ubuntu"]
        self._archive = self._ubuntu.main_archive
        self._series = self._ubuntu.getSeries(name_or_version=self.series)

    def lp_user_name(self) -> str:
        return self._lp.me.name

    def get_queue_items(self, status: str = QUEUE_STATUS_UNAPPROVED) -> list[QueueItem]:
        """Fetch all items in the upload queue for the configured series.

        Args:
            status: The Launchpad queue status string. Defaults to Unapproved.

        Returns:
            A list of QueueItem dataclass instances.

        """
        self._log(f"series.getPackageUploads(status={status!r})")
        uploads = self._series.getPackageUploads(status=status)
        items: list[QueueItem] = []
        for upload in uploads:
            name = upload.package_name or upload.display_name
            version = upload.package_version or ""
            is_sync = _is_sync(upload)
            authors = _build_authors(upload, is_sync)
            item = QueueItem(
                source_name=name,
                version=version,
                component=upload.component_name or "",
                section=upload.section_name or "",
                archive_url=upload.self_link,
                date_created=str(upload.date_created),
                status=upload.status,
                is_sync=is_sync,
                changes_file_url=upload.changes_file_url,
                authors=authors,
                lp_item=upload,
            )
            items.append(item)
            self._log("Adding %s" % item)
        return items

    def get_debdiff(self, item: QueueItem) -> str:
        """Compute the debdiff for a queue item.

        Compares the currently published version in the archive with the
        new version in the queue.  Falls back to displaying the changes
        file content when no previous version exists or when debdiff is
        not installed.

        For sync'd packages whose source files are not available via
        Launchpad, the new version is fetched from the Debian archive.

        Args:
            item: The queue item to get the debdiff for.

        Returns:
            The debdiff output as a string, or the changes file content.

        """
        current = self._get_current_source(item.source_name)
        if current is None:
            return self._get_changes_content(item)

        self._log(
            f"Found current source package: {current.source_package_name}/{current.source_package_version}"
        )

        work_dir = self.work_dir / item.source_name
        work_dir.mkdir(parents=True, exist_ok=True)
        work_dir = str(work_dir)

        old_dsc = _download_source_files(current.sourceFileUrls(), work_dir)

        if not item.is_sync:
            # Try LP source files first; silently fall back for syncs.
            try:
                self._log(f"Fetching {item.display_name} from Ubuntu archive")
                new_dsc = _download_source_files(item.lp_item.sourceFileUrls(), work_dir)
            except (OSError, urllib.error.URLError) as e:
                self._log("LP source files unavailable for %s (%s)" % (item.display_name, e))
                new_dsc = None

        #  For synced packages: fetch from the Debian archive via LP.
        if item.is_sync:
            try:
                self._log(f"Fetching {item.display_name} from Debian archive")
                new_dsc = self._get_debian_source(item.source_name, item.version, work_dir)
            except (OSError, urllib.error.URLError) as e:
                self._log("LP source files unavailable for %s (%s)" % (item.display_name, e))
                new_dsc = None

        if old_dsc is None or new_dsc is None:
            return self._get_changes_content(item)
        return self._run_debdiff(old_dsc, new_dsc)

    def _run_debdiff(self, old_dsc: str, new_dsc: str) -> str:
        """Run some diff between two .dsc files and return the output."""
        # Get a diffoscope HTML output for very rich diffing
        try:
            output = self.work_dir / (
                Path(old_dsc).stem + "_" + Path(new_dsc).stem + "_debdiff.html"
            )
            subprocess.run(["diffoscope", "--html", str(output), old_dsc, new_dsc], timeout=120)
            subprocess.run(["xdg-open", str(output)], timeout=120)
        except FileNotFoundError:
            self._log(
                "(diffoscope not found — install at least the 'diffoscope-minimal' package: sudo apt install diffoscope-minimal)"
            )
        # Display debdiff in the main console output
        try:
            result = subprocess.run(
                ["debdiff", old_dsc, new_dsc],
                capture_output=True,
                text=True,
                timeout=120,
            )
            # debdiff returns 0 for no diff, 1 for diff found (both are OK)
            if result.returncode <= 1:
                return result.stdout or "(no differences found)"
            return result.stderr or f"(debdiff exited with code {result.returncode})"
        except FileNotFoundError:
            return "(debdiff not found — install the 'devscripts' package: sudo apt install devscripts)"
        except subprocess.TimeoutExpired:
            return "(debdiff timed out after 120 seconds)"

    def accept(self, item: QueueItem) -> None:
        """Accept a queue item.

        Args:
            item: The queue item to accept.

        """
        self._log(f"item.acceptFromQueue() [{item.display_name}]")
        item.lp_item.acceptFromQueue()

    def reject(self, item: QueueItem, comment: str) -> None:
        """Reject a queue item with a comment.

        Args:
            item: The queue item to reject.
            comment: The rejection reason/comment.

        """
        self._log(f"item.rejectFromQueue(comment=...) [{item.display_name}]")
        item.lp_item.rejectFromQueue(comment=comment)

    def get_all_series(self) -> list[tuple[str, str, str]]:
        """Return all Ubuntu series as ``(name, version, status)`` tuples."""
        result: list[tuple[str, str, str]] = []
        for s in self._ubuntu.series:
            self._log(f"{s.name}: {s.status}")
            if s.status != "Obsolete":
                result.append((s.name, s.version, s.status))
        return result

    def switch_series(self, series_name: str) -> None:
        """Change the active series to *series_name*.

        After calling this the next :meth:`get_queue_items` call will
        operate on the new series.

        """
        self._series = self._ubuntu.getSeries(name_or_version=series_name)
        self.series = series_name

    def get_debian_tracker_url(self, source_name: str) -> str:
        """Return the Debian tracker URL for a source package.

        Args:
            source_name: The source package name.

        Returns:
            The URL to the Debian tracker page.

        """
        return f"https://tracker.debian.org/pkg/{source_name}"

    def _get_current_source(self, source_name: str) -> object | None:
        """Return the currently published source in the archive, or None."""
        sources = self._archive.getPublishedSources(
            source_name=source_name,
            exact_match=True,
            status="Published",
            distro_series=self._series,
        )
        return sources[0] if sources else None

    def _get_changes_content(self, item: QueueItem) -> str:
        """Fetch and return the changes file content for an item.

        This is used as a fallback when debdiff is not possible (e.g.,
        new package with no previous version in the archive).
        """
        if item.changes_file_url is None:
            return "(no changes file available)"
        try:
            with urllib.request.urlopen(item.changes_file_url) as resp:  # noqa: S310
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            self._log("Failed to fetch changes file (%s)" % e)
            return "(failed to fetch changes file)"

    def _ensure_debian_archive(self) -> None:
        """Lazily initialise the Debian archive reference via Launchpad."""
        if self._debian_archive is None:
            debian = self._lp.distributions["debian"]
            self._debian_archive = debian.main_archive

    def _get_debian_source(self, source_name: str, version: str, dest: str) -> str | None:
        """Download source files for *version* from Debian via the Launchpad API.

        Uses ``lp.distributions["debian"].main_archive.getPublishedSources()``
        to locate the published source package, then downloads the files
        referenced by ``sourceFileUrls()``.

        Returns:
            The local path to the downloaded ``.dsc``, or ``None`` on failure.

        """
        self._ensure_debian_archive()
        try:
            sources = self._debian_archive.getPublishedSources(
                source_name=source_name,
                version=version,
                exact_match=True,
                status="Published",
            )
        except Exception:
            self._log("Failed to query Debian archive for %s %s" % (source_name, version))
            return None

        if not sources:
            self._log("No published Debian source found for %s %s" % (source_name, version))
            return None

        try:
            urls = sources[0].sourceFileUrls()
        except Exception as e:
            self._log("Failed to get source file URLs for %s %s (%s)" % (source_name, version, e))
            return None

        return _download_source_files(urls, dest)


def _is_sync(upload: object) -> bool:
    """Detect whether an upload is a sync from Debian."""
    return upload.contains_copy


def _extract_lp_username(link: str | None) -> str | None:
    """Extract a Launchpad username from an API person link.

    Launchpad person links have the form
    ``https://api.launchpad.net/devel/~username``.

    Returns:
        The username string, or ``None`` when *link* is ``None`` or does
        not contain the expected ``/~`` separator.

    """
    if link and "/~" in link:
        return link.rsplit("/~", 1)[-1]
    return None


def _build_authors(upload: object, is_sync: bool) -> str:
    """Build the "Author(s)" string for a queue upload.

    For syncs the requestor is shown.  For regular uploads the signer
    (uploader) is shown, plus the sponsor when the two differ.

    """
    if is_sync:
        requestor = _extract_lp_username(
            getattr(upload, "package_copy_requestor_link", None),
        )
        return requestor or ""

    signer = _extract_lp_username(
        getattr(upload, "signing_key_owner_link", None),
    )
    sponsor = _extract_lp_username(
        getattr(upload, "sponsor_link", None),
    )

    if signer and sponsor and signer != sponsor:
        return f"{signer}, sponsor: {sponsor}"
    return signer or ""


def _download_source_files(urls: list[str], dest: str) -> str | None:
    """Download source files and return the path to the .dsc file."""
    dsc_path = None
    for url in urls:
        filename = url.rsplit("/", 1)[-1]
        filepath = Path(dest) / filename
        if filename.endswith(".dsc"):
            dsc_path = str(filepath)
        if filepath.exists():
            continue
        urllib.request.urlretrieve(url, filepath)  # noqa: S310
    return dsc_path
