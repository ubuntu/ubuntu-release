"""Tests for the launchpad module."""

from lp_queue.launchpad import LaunchpadQueue, QueueItem


class TestQueueItem:
    """Tests for the QueueItem dataclass."""

    def test_display_name(self):
        """Test that display_name returns name and version."""
        item = QueueItem(
            source_name="hello",
            version="2.10-3",
            component="main",
            section="devel",
            archive_url="https://launchpad.net/ubuntu/+archive/primary",
            date_created="2025-01-01",
            status="Unapproved",
            is_sync=False,
            changes_file_url=None,
        )
        assert item.display_name == "hello 2.10-3"


class TestLaunchpadQueue:
    """Tests for the LaunchpadQueue class."""

    def test_default_series(self):
        """Test that the default series is set correctly."""
        lp = LaunchpadQueue()
        assert lp.series == "resolute"

    def test_custom_series(self):
        """Test that a custom series can be specified."""
        lp = LaunchpadQueue(series="noble")
        assert lp.series == "noble"

    def test_debian_tracker_url(self):
        """Test that Debian tracker URLs are built correctly."""
        lp = LaunchpadQueue()
        url = lp.get_debian_tracker_url("hello")
        assert url == "https://tracker.debian.org/pkg/hello"
