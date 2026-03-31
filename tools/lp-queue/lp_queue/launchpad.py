"""Launchpad API interactions for the upload queue."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default Ubuntu series to operate on.
DEFAULT_SERIES = "resolute"

# Launchpad queue states.
QUEUE_STATE_NEW = 0
QUEUE_STATE_UNAPPROVED = 1
QUEUE_STATE_ACCEPTED = 2
QUEUE_STATE_DONE = 3
QUEUE_STATE_REJECTED = 4


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

    def connect(self) -> None:
        """Authenticate and connect to Launchpad.

        Uses launchpadlib to obtain OAuth credentials and connect
        to the production Launchpad instance.
        """
        # TODO: implement Launchpad connection
        raise NotImplementedError

    def get_queue_items(self, queue_state: int = QUEUE_STATE_UNAPPROVED) -> list[QueueItem]:
        """Fetch all items in the upload queue for the configured series.

        Args:
            queue_state: The Launchpad queue state to query. Defaults to Unapproved.

        Returns:
            A list of QueueItem dataclass instances.

        """
        # TODO: implement queue item fetching
        raise NotImplementedError

    def get_debdiff(self, item: QueueItem) -> str:
        """Compute the debdiff for a queue item.

        Compares the currently published version in the archive with the new
        version in the queue. For syncs from Debian, this fetches the Debian
        source and compares against the current Ubuntu version.

        Args:
            item: The queue item to get the debdiff for.

        Returns:
            The debdiff output as a string.

        """
        # TODO: implement debdiff generation
        raise NotImplementedError

    def accept(self, item: QueueItem) -> None:
        """Accept a queue item.

        Args:
            item: The queue item to accept.

        """
        # TODO: implement accept action
        raise NotImplementedError

    def reject(self, item: QueueItem, comment: str) -> None:
        """Reject a queue item with a comment.

        Args:
            item: The queue item to reject.
            comment: The rejection reason/comment.

        """
        # TODO: implement reject action
        raise NotImplementedError

    def get_debian_tracker_url(self, source_name: str) -> str:
        """Return the Debian tracker URL for a source package.

        Args:
            source_name: The source package name.

        Returns:
            The URL to the Debian tracker page.

        """
        return f"https://tracker.debian.org/pkg/{source_name}"
