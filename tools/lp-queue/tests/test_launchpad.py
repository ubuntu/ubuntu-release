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

    def test_log_callback(self):
        """Test that _log invokes the registered callback."""
        lp = LaunchpadQueue()
        messages: list[str] = []
        lp.set_log_callback(messages.append)
        lp._log("hello")
        assert messages == ["hello"]

    def test_log_no_callback(self):
        """Test that _log is a no-op when no callback is registered."""
        lp = LaunchpadQueue()
        # Should not raise
        lp._log("ignored")

    def test_get_all_series(self):
        """Test get_all_series returns non-Obsolete series tuples."""
        lp = LaunchpadQueue()

        mock_series_1 = MagicMock()
        mock_series_1.name = "resolute"
        mock_series_1.version = "26.04"
        mock_series_1.status = "Active Development"

        mock_series_2 = MagicMock()
        mock_series_2.name = "noble"
        mock_series_2.version = "24.04"
        mock_series_2.status = "Supported"

        mock_series_3 = MagicMock()
        mock_series_3.name = "trusty"
        mock_series_3.version = "14.04"
        mock_series_3.status = "Obsolete"

        mock_ubuntu = MagicMock()
        mock_ubuntu.series = [mock_series_1, mock_series_2, mock_series_3]
        lp._ubuntu = mock_ubuntu

        result = lp.get_all_series()

        # Obsolete series are filtered out
        assert len(result) == 2
        assert result[0] == ("resolute", "26.04", "Active Development")
        assert result[1] == ("noble", "24.04", "Supported")

    def test_switch_series(self):
        """Test switch_series updates the active series."""
        lp = LaunchpadQueue()

        mock_ubuntu = MagicMock()
        mock_new_series = MagicMock()
        mock_ubuntu.getSeries.return_value = mock_new_series
        lp._ubuntu = mock_ubuntu

        lp.switch_series("noble")

        mock_ubuntu.getSeries.assert_called_once_with(name_or_version="noble")
        assert lp.series == "noble"
        assert lp._series is mock_new_series


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


class TestGetDebianSource:
    """Tests for the LaunchpadQueue._get_debian_source method."""

    def test_success(self, tmp_path):
        """Successfully fetch source files from Debian via LP API."""
        lp = LaunchpadQueue()

        mock_lp = MagicMock()
        mock_debian = MagicMock()
        mock_debian_archive = MagicMock()
        mock_lp.distributions.__getitem__.return_value = mock_debian
        mock_debian.main_archive = mock_debian_archive

        mock_source = MagicMock()
        mock_source.sourceFileUrls.return_value = [
            "https://example.com/hello_2.10.orig.tar.gz",
            "https://example.com/hello_2.10-3.debian.tar.xz",
            "https://example.com/hello_2.10-3.dsc",
        ]
        mock_debian_archive.getPublishedSources.return_value = [mock_source]
        lp._lp = mock_lp

        with patch("lp_queue.launchpad.urllib.request.urlretrieve"):
            result = lp._get_debian_source("hello", "2.10-3", str(tmp_path))

        assert result is not None
        assert result.endswith("hello_2.10-3.dsc")
        mock_debian_archive.getPublishedSources.assert_called_once_with(
            source_name="hello",
            version="2.10-3",
            exact_match=True,
            status="Published",
        )

    def test_no_sources_found(self, tmp_path):
        """Return None when no Debian source is found."""
        lp = LaunchpadQueue()

        mock_lp = MagicMock()
        mock_debian = MagicMock()
        mock_debian_archive = MagicMock()
        mock_lp.distributions.__getitem__.return_value = mock_debian
        mock_debian.main_archive = mock_debian_archive
        mock_debian_archive.getPublishedSources.return_value = []
        lp._lp = mock_lp

        result = lp._get_debian_source("nonexistent", "1.0-1", str(tmp_path))
        assert result is None

    def test_api_error(self, tmp_path):
        """Return None when the LP API call raises an exception."""
        lp = LaunchpadQueue()

        mock_lp = MagicMock()
        mock_debian = MagicMock()
        mock_debian_archive = MagicMock()
        mock_lp.distributions.__getitem__.return_value = mock_debian
        mock_debian.main_archive = mock_debian_archive
        mock_debian_archive.getPublishedSources.side_effect = Exception("API error")
        lp._lp = mock_lp

        result = lp._get_debian_source("hello", "2.10-3", str(tmp_path))
        assert result is None

    def test_source_file_urls_error(self, tmp_path):
        """Return None when sourceFileUrls() raises an exception."""
        lp = LaunchpadQueue()

        mock_lp = MagicMock()
        mock_debian = MagicMock()
        mock_debian_archive = MagicMock()
        mock_lp.distributions.__getitem__.return_value = mock_debian
        mock_debian.main_archive = mock_debian_archive

        mock_source = MagicMock()
        mock_source.sourceFileUrls.side_effect = Exception("URL error")
        mock_debian_archive.getPublishedSources.return_value = [mock_source]
        lp._lp = mock_lp

        result = lp._get_debian_source("hello", "2.10-3", str(tmp_path))
        assert result is None

    def test_caches_debian_archive(self, tmp_path):
        """The Debian archive reference is lazily cached after first use."""
        lp = LaunchpadQueue()

        mock_lp = MagicMock()
        mock_debian = MagicMock()
        mock_debian_archive = MagicMock()
        mock_lp.distributions.__getitem__.return_value = mock_debian
        mock_debian.main_archive = mock_debian_archive
        mock_debian_archive.getPublishedSources.return_value = []
        lp._lp = mock_lp

        lp._get_debian_source("hello", "1.0-1", str(tmp_path))
        lp._get_debian_source("world", "2.0-1", str(tmp_path))

        # distributions["debian"] should only be accessed once
        mock_lp.distributions.__getitem__.assert_called_once_with("debian")

    def test_version_with_epoch(self, tmp_path):
        """Epochs are passed through to the LP API as-is."""
        lp = LaunchpadQueue()

        mock_lp = MagicMock()
        mock_debian = MagicMock()
        mock_debian_archive = MagicMock()
        mock_lp.distributions.__getitem__.return_value = mock_debian
        mock_debian.main_archive = mock_debian_archive
        mock_debian_archive.getPublishedSources.return_value = []
        lp._lp = mock_lp

        lp._get_debian_source("hello", "2:1.0-1", str(tmp_path))

        mock_debian_archive.getPublishedSources.assert_called_once_with(
            source_name="hello",
            version="2:1.0-1",
            exact_match=True,
            status="Published",
        )


class TestDebdiffSyncFallback:
    """Tests for the Debian archive fallback in get_debdiff."""

    @patch("lp_queue.launchpad._download_source_files")
    @patch("lp_queue.launchpad._run_debdiff")
    def test_sync_fallback_used(self, mock_debdiff, mock_dl_source):
        """When LP source files are empty for a sync, Debian LP fallback is used."""
        lp = LaunchpadQueue()

        mock_current = MagicMock()
        mock_current.sourceFileUrls.return_value = [
            "https://lp.example.com/hello_2.10-2ubuntu1.dsc",
        ]
        lp._archive = MagicMock()
        lp._archive.getPublishedSources.return_value = [mock_current]
        lp._series = MagicMock()

        # Set up the Debian archive mock
        mock_lp_obj = MagicMock()
        mock_debian = MagicMock()
        mock_debian_archive = MagicMock()
        mock_lp_obj.distributions.__getitem__.return_value = mock_debian
        mock_debian.main_archive = mock_debian_archive

        mock_deb_source = MagicMock()
        mock_deb_source.sourceFileUrls.return_value = [
            "https://example.com/hello_2.10-3.dsc",
        ]
        mock_debian_archive.getPublishedSources.return_value = [mock_deb_source]
        lp._lp = mock_lp_obj

        mock_lp_item = MagicMock()
        mock_lp_item.sourceFileUrls.return_value = []
        item = QueueItem(
            source_name="hello",
            version="2.10-3",
            component="main",
            section="devel",
            archive_url="",
            date_created="2025-01-01",
            status="Unapproved",
            is_sync=True,
            changes_file_url=None,
            lp_item=mock_lp_item,
        )

        # First call (old) returns a .dsc path, second call (new, empty) returns None,
        # third call (Debian fallback) returns the new .dsc path.
        mock_dl_source.side_effect = ["/tmp/old.dsc", None, "/tmp/new.dsc"]
        mock_debdiff.return_value = "diff output"

        result = lp.get_debdiff(item)

        assert result == "diff output"
        mock_debian_archive.getPublishedSources.assert_called_once_with(
            source_name="hello",
            version="2.10-3",
            exact_match=True,
            status="Published",
        )
        mock_debdiff.assert_called_once_with("/tmp/old.dsc", "/tmp/new.dsc")

    @patch("lp_queue.launchpad._download_source_files")
    @patch("lp_queue.launchpad._run_debdiff")
    def test_non_sync_no_fallback(self, mock_debdiff, mock_dl_source):
        """Non-sync packages should NOT trigger the Debian fallback."""
        lp = LaunchpadQueue()

        mock_current = MagicMock()
        mock_current.sourceFileUrls.return_value = []
        lp._archive = MagicMock()
        lp._archive.getPublishedSources.return_value = [mock_current]
        lp._series = MagicMock()

        mock_lp_item = MagicMock()
        mock_lp_item.sourceFileUrls.return_value = []
        item = QueueItem(
            source_name="hello",
            version="2.10-3ubuntu1",
            component="main",
            section="devel",
            archive_url="",
            date_created="2025-01-01",
            status="Unapproved",
            is_sync=False,
            changes_file_url=None,
            lp_item=mock_lp_item,
        )

        mock_dl_source.return_value = None

        result = lp.get_debdiff(item)

        assert "(no changes file available)" in result

    @patch("lp_queue.launchpad._download_source_files")
    def test_sync_fallback_lp_throws(self, mock_dl_source):
        """When LP sourceFileUrls() throws for a sync, Debian LP fallback is used."""
        lp = LaunchpadQueue()

        mock_current = MagicMock()
        mock_current.sourceFileUrls.return_value = []
        lp._archive = MagicMock()
        lp._archive.getPublishedSources.return_value = [mock_current]
        lp._series = MagicMock()

        # Set up the Debian archive mock that returns no sources
        mock_lp_obj = MagicMock()
        mock_debian = MagicMock()
        mock_debian_archive = MagicMock()
        mock_lp_obj.distributions.__getitem__.return_value = mock_debian
        mock_debian.main_archive = mock_debian_archive
        mock_debian_archive.getPublishedSources.return_value = []
        lp._lp = mock_lp_obj

        mock_lp_item = MagicMock()
        mock_lp_item.sourceFileUrls.side_effect = OSError("API error")
        item = QueueItem(
            source_name="hello",
            version="2.10-3",
            component="main",
            section="devel",
            archive_url="",
            date_created="2025-01-01",
            status="Unapproved",
            is_sync=True,
            changes_file_url=None,
            lp_item=mock_lp_item,
        )

        mock_dl_source.return_value = "/tmp/old.dsc"

        result = lp.get_debdiff(item)

        # Debian fallback was attempted via LP API
        mock_debian_archive.getPublishedSources.assert_called_once()
        # But it returned no sources, so falls back to changes content
        assert "(no changes file available)" in result
