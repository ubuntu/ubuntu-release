"""Tests for the launchpad module."""

import subprocess
from unittest.mock import MagicMock, patch

from lp_queue.launchpad import (
    LaunchpadQueue,
    QueueItem,
    _download_source_files,
    _is_sync,
    _run_debdiff,
)

# ---------------------------------------------------------------------------
# QueueItem tests
# ---------------------------------------------------------------------------


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

    def test_display_name_with_ubuntu_version(self):
        item = QueueItem(
            source_name="bash",
            version="5.2-1ubuntu1",
            component="main",
            section="shells",
            archive_url="",
            date_created="2025-06-01",
            status="Unapproved",
            is_sync=False,
            changes_file_url=None,
        )
        assert item.display_name == "bash 5.2-1ubuntu1"


# ---------------------------------------------------------------------------
# LaunchpadQueue tests
# ---------------------------------------------------------------------------


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

    def test_connect(self):
        """Test that connect() calls Launchpad.login_with correctly."""
        mock_lp_class = MagicMock()
        mock_lp = MagicMock()
        mock_lp_class.login_with.return_value = mock_lp

        lp_mod = MagicMock(Launchpad=mock_lp_class)
        with patch.dict("sys.modules", {"launchpadlib": lp_mod, "launchpadlib.launchpad": lp_mod}):
            lp = LaunchpadQueue()
            lp.connect()

        mock_lp_class.login_with.assert_called_once_with(
            "lp-queue-tui", "production", version="devel"
        )

    def test_get_queue_items(self):
        """Test get_queue_items converts LP objects to QueueItems."""
        lp = LaunchpadQueue()

        mock_upload = MagicMock()
        mock_upload.package_name = "hello"
        mock_upload.display_name = "hello"
        mock_upload.package_version = "2.10-3"
        mock_upload.component_name = "main"
        mock_upload.section_name = "devel"
        mock_upload.self_link = "https://api.launchpad.net/devel/..."
        mock_upload.date_created = "2025-01-01T00:00:00+00:00"
        mock_upload.status = "Unapproved"
        mock_upload.changes_file_url = "https://example.com/changes"
        mock_upload.copy_source_archive_link = None

        mock_series = MagicMock()
        mock_series.getPackageUploads.return_value = [mock_upload]
        lp._series = mock_series

        items = lp.get_queue_items()

        assert len(items) == 1
        assert items[0].source_name == "hello"
        assert items[0].version == "2.10-3"
        assert items[0].component == "main"
        assert items[0].status == "Unapproved"

    def test_accept(self):
        """Test accept delegates to the LP item."""
        mock_lp_item = MagicMock()
        item = QueueItem(
            source_name="hello",
            version="2.10-3",
            component="main",
            section="devel",
            archive_url="",
            date_created="2025-01-01",
            status="Unapproved",
            is_sync=False,
            changes_file_url=None,
            lp_item=mock_lp_item,
        )
        lp = LaunchpadQueue()
        lp.accept(item)
        mock_lp_item.acceptFromQueue.assert_called_once()

    def test_reject(self):
        """Test reject delegates to the LP item with comment."""
        mock_lp_item = MagicMock()
        item = QueueItem(
            source_name="hello",
            version="2.10-3",
            component="main",
            section="devel",
            archive_url="",
            date_created="2025-01-01",
            status="Unapproved",
            is_sync=False,
            changes_file_url=None,
            lp_item=mock_lp_item,
        )
        lp = LaunchpadQueue()
        lp.reject(item, "FTBFS on amd64")
        mock_lp_item.rejectFromQueue.assert_called_once_with(comment="FTBFS on amd64")

    def test_get_changes_content_no_url(self):
        """Test _get_changes_content with no URL returns a message."""
        lp = LaunchpadQueue()
        item = QueueItem(
            source_name="hello",
            version="2.10-3",
            component="main",
            section="devel",
            archive_url="",
            date_created="",
            status="Unapproved",
            is_sync=False,
            changes_file_url=None,
        )
        result = lp._get_changes_content(item)
        assert "(no changes file available)" in result


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestIsSyncHelper:
    """Tests for the _is_sync helper."""

    def test_ubuntu_version_not_sync(self):
        upload = MagicMock()
        upload.copy_source_archive_link = None
        assert _is_sync("2.10-3ubuntu1", upload) is False

    def test_debian_version_with_copy_archive(self):
        upload = MagicMock()
        upload.copy_source_archive_link = "https://api.launchpad.net/..."
        assert _is_sync("2.10-3", upload) is True

    def test_debian_version_no_copy_archive(self):
        upload = MagicMock()
        upload.copy_source_archive_link = None
        assert _is_sync("2.10-3", upload) is False

    def test_missing_attribute(self):
        upload = MagicMock(spec=[])
        assert _is_sync("2.10-3", upload) is False


class TestRunDebdiff:
    """Tests for the _run_debdiff helper."""

    @patch("lp_queue.launchpad.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="diff output", stderr="")
        assert _run_debdiff("/a.dsc", "/b.dsc") == "diff output"

    @patch("lp_queue.launchpad.subprocess.run")
    def test_diff_found(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="differences", stderr="")
        assert _run_debdiff("/a.dsc", "/b.dsc") == "differences"

    @patch("lp_queue.launchpad.subprocess.run")
    def test_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="error msg")
        assert "error msg" in _run_debdiff("/a.dsc", "/b.dsc")

    @patch("lp_queue.launchpad.subprocess.run", side_effect=FileNotFoundError)
    def test_not_installed(self, mock_run):
        result = _run_debdiff("/a.dsc", "/b.dsc")
        assert "devscripts" in result

    @patch(
        "lp_queue.launchpad.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="debdiff", timeout=120),
    )
    def test_timeout(self, mock_run):
        result = _run_debdiff("/a.dsc", "/b.dsc")
        assert "timed out" in result


class TestDownloadSourceFiles:
    """Tests for the _download_source_files helper."""

    @patch("lp_queue.launchpad.urllib.request.urlretrieve")
    def test_returns_dsc_path(self, mock_urlretrieve, tmp_path):
        urls = [
            "https://example.com/hello_2.10-3.dsc",
            "https://example.com/hello_2.10.orig.tar.gz",
        ]
        result = _download_source_files(urls, str(tmp_path))
        assert result is not None
        assert result.endswith(".dsc")

    @patch("lp_queue.launchpad.urllib.request.urlretrieve")
    def test_no_dsc(self, mock_urlretrieve, tmp_path):
        urls = ["https://example.com/hello_2.10.orig.tar.gz"]
        result = _download_source_files(urls, str(tmp_path))
        assert result is None
