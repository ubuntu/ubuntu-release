"""Launchpad API interactions for the upload queue."""

from __future__ import annotations

import logging
import subprocess
import tempfile
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Default Ubuntu series to operate on.
DEFAULT_SERIES = "resolute"

# Debian archive base URL for fetching source files.
DEBIAN_ARCHIVE_URL = "https://deb.debian.org/debian"

# Debian pool components to try when locating source packages.
DEBIAN_COMPONENTS = ("main", "contrib", "non-free", "non-free-firmware")

# Launchpad queue status strings expected by the API.
QUEUE_STATUS_NEW = "New"
QUEUE_STATUS_UNAPPROVED = "Unapproved"
QUEUE_STATUS_ACCEPTED = "Accepted"
QUEUE_STATUS_DONE = "Done"
QUEUE_STATUS_REJECTED = "Rejected"


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
    lp_item: object | None = None

    @property
    def display_name(self) -> str:
        """Return a display-friendly name for the item."""
        return f"{self.source_name} {self.version}"


class LaunchpadQueue:
    """Interface to the Launchpad upload queue."""

    def __init__(self, series: str = DEFAULT_SERIES):
        self.series = series
        self._lp = None
        self._ubuntu = None
        self._archive = None
        self._series = None
        self._log_callback: Callable[[str], None] | None = None

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

        self._log("Launchpad.login_with('lp-queue-tui', 'production', version='devel')")
        self._lp = Launchpad.login_with(
            "lp-queue-tui",
            "production",
            version="devel",
        )
        self._log("distributions['ubuntu']")
        self._ubuntu = self._lp.distributions["ubuntu"]
        self._log("ubuntu.main_archive")
        self._archive = self._ubuntu.main_archive
        self._log(f"ubuntu.getSeries(name_or_version={self.series!r})")
        self._series = self._ubuntu.getSeries(name_or_version=self.series)

    def lp_user_name(self) -> str:
        self._log("lp.me.name")
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
            item = QueueItem(
                source_name=name,
                version=version,
                component=upload.component_name or "",
                section=upload.section_name or "",
                archive_url=upload.self_link,
                date_created=str(upload.date_created),
                status=upload.status,
                is_sync=_is_sync(version, upload),
                changes_file_url=upload.changes_file_url,
                lp_item=upload,
            )
            items.append(item)
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
        self._log(f"get_debdiff({item.display_name})")
        current = self._get_current_source(item.source_name)
        if current is None:
            return self._get_changes_content(item)

        with tempfile.TemporaryDirectory() as tmpdir:
            old_dsc = _download_source_files(current.sourceFileUrls(), tmpdir)

            # Try LP source files first; silently fall back for syncs.
            try:
                new_dsc = _download_source_files(item.lp_item.sourceFileUrls(), tmpdir)
            except Exception:
                new_dsc = None

            # Fallback for synced packages: fetch from the Debian archive.
            if new_dsc is None and item.is_sync:
                self._log(
                    f"Fetching {item.display_name} from Debian archive (sync fallback)"
                )
                new_dsc = _download_debian_source(item.source_name, item.version, tmpdir)

            if old_dsc is None or new_dsc is None:
                return self._get_changes_content(item)
            return _run_debdiff(old_dsc, new_dsc)

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
        self._log("ubuntu.series_collection")
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
        self._log(f"ubuntu.getSeries(name_or_version={series_name!r})")
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
        self._log(
            f"archive.getPublishedSources(source_name={source_name!r}, "
            f"exact_match=True, status='Published')"
        )
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
        except Exception:
            logger.exception("Failed to fetch changes file")
            return "(failed to fetch changes file)"


def _is_sync(version: str, upload: object) -> bool:
    """Heuristic to detect whether an upload is a sync from Debian.

    Synced packages typically lack an ``ubuntuN`` version suffix and may
    have a ``copy_source_archive`` set on the upload.
    """
    if "ubuntu" in version:
        return False
    try:
        return upload.copy_source_archive_link is not None
    except AttributeError:
        return False


def _download_source_files(urls: list[str], dest: str) -> str | None:
    """Download source files and return the path to the .dsc file."""
    dsc_path = None
    for url in urls:
        filename = url.rsplit("/", 1)[-1]
        filepath = Path(dest) / filename
        urllib.request.urlretrieve(url, filepath)  # noqa: S310
        if filename.endswith(".dsc"):
            dsc_path = str(filepath)
    return dsc_path


def _run_debdiff(old_dsc: str, new_dsc: str) -> str:
    """Run debdiff between two .dsc files and return the output."""
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
        return (
            "(debdiff not found — install the 'devscripts' package: sudo apt install devscripts)"
        )
    except subprocess.TimeoutExpired:
        return "(debdiff timed out after 120 seconds)"


def _debian_pool_prefix(source_name: str) -> str:
    """Return the Debian pool directory prefix for a source package.

    Packages starting with ``lib`` use a four-character prefix (e.g.
    ``liba`` for ``libapt``); all others use their first character.
    """
    if source_name.startswith("lib") and len(source_name) > 3:
        return source_name[:4]
    return source_name[0]


def _strip_epoch(version: str) -> str:
    """Remove the epoch from a Debian version string.

    ``"2:1.0-1"`` → ``"1.0-1"``, ``"1.0-1"`` → ``"1.0-1"``.
    """
    if ":" in version:
        return version.split(":", 1)[1]
    return version


def _parse_dsc_files(dsc_content: str) -> list[str]:
    """Parse a ``.dsc`` file and return the filenames listed in ``Files:``.

    Returns:
        A list of filenames referenced by the .dsc.

    """
    files: list[str] = []
    in_files_section = False
    for line in dsc_content.splitlines():
        if line.startswith("Files:"):
            in_files_section = True
            continue
        if in_files_section:
            if line.startswith(" "):
                parts = line.split()
                if len(parts) >= 3:
                    files.append(parts[-1])
            else:
                break
    return files


def _download_debian_source(source_name: str, version: str, dest: str) -> str | None:
    """Download source files for *version* from the Debian archive.

    Tries each Debian component (main, contrib, …) until the ``.dsc``
    is found, then downloads the files it references.

    Returns:
        The local path to the downloaded ``.dsc``, or ``None`` on failure.

    """
    clean_version = _strip_epoch(version)
    prefix = _debian_pool_prefix(source_name)
    dsc_filename = f"{source_name}_{clean_version}.dsc"

    for component in DEBIAN_COMPONENTS:
        base_url = f"{DEBIAN_ARCHIVE_URL}/pool/{component}/{prefix}/{source_name}"
        dsc_url = f"{base_url}/{dsc_filename}"
        try:
            dsc_path = Path(dest) / dsc_filename
            urllib.request.urlretrieve(dsc_url, dsc_path)  # noqa: S310
        except Exception:
            continue

        # .dsc found in this component – download the referenced files.
        try:
            dsc_content = dsc_path.read_text(encoding="utf-8", errors="replace")
            for filename in _parse_dsc_files(dsc_content):
                file_url = f"{base_url}/{filename}"
                filepath = Path(dest) / filename
                urllib.request.urlretrieve(file_url, filepath)  # noqa: S310
        except Exception:
            logger.exception("Failed to download Debian source files")
            return None

        return str(dsc_path)

    return None
