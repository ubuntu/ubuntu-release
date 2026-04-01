"""Tests for the TUI application."""

from unittest.mock import MagicMock

from textual.widgets import DataTable, RichLog

from lp_queue.app import QueueApp, RejectScreen, ReviewScreen
from lp_queue.launchpad import LaunchpadQueue, QueueItem


def _make_item(**overrides):
    """Create a QueueItem with sensible defaults."""
    defaults = {
        "source_name": "hello",
        "version": "2.10-3",
        "component": "main",
        "section": "devel",
        "archive_url": "",
        "date_created": "2025-01-01",
        "status": "Unapproved",
        "is_sync": False,
        "changes_file_url": None,
        "lp_item": MagicMock(),
    }
    defaults.update(overrides)
    return QueueItem(**defaults)


class TestQueueAppTable:
    """Tests for the main QueueApp table population."""

    async def test_populate_table(self):
        """Test that _populate_table fills the DataTable correctly."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            app.queue_items = [
                _make_item(source_name="hello", version="2.10-3"),
                _make_item(source_name="bash", version="5.2-1ubuntu1", is_sync=False),
            ]
            app._populate_table()
            table = app.query_one(DataTable)
            assert table.row_count == 2

    async def test_empty_queue(self):
        """Test that an empty queue displays zero rows."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            app.queue_items = []
            app._populate_table()
            table = app.query_one(DataTable)
            assert table.row_count == 0

    async def test_get_selected_item_empty(self):
        """Test that _get_selected_item returns None for an empty table."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            result = app._get_selected_item()
            assert result is None


class TestReviewScreen:
    """Tests for the ReviewScreen modal."""

    async def test_review_screen_displays_content(self):
        """Test that the ReviewScreen shows the debdiff text."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            item = _make_item()
            screen = ReviewScreen(item, "--- a/file\n+++ b/file\n")
            app.push_screen(screen)
            await _pilot.pause()
            assert app.screen is screen


class TestRejectScreen:
    """Tests for the RejectScreen modal."""

    async def test_reject_screen_dismiss_on_escape(self):
        """Test that pressing escape dismisses the reject screen."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            item = _make_item()
            screen = RejectScreen(item)
            app.push_screen(screen)
            await _pilot.pause()
            assert app.screen is screen
            await _pilot.press("escape")
            await _pilot.pause()
            assert app.screen is not screen


class TestDebugPanel:
    """Tests for the toggleable debug log panel."""

    async def test_debug_panel_hidden_by_default(self):
        """Test that the debug panel is hidden on startup."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            panel = app.query_one("#debug-panel")
            assert "visible" not in panel.classes

    async def test_toggle_debug_panel(self):
        """Test that pressing ~ toggles the debug panel visibility."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            panel = app.query_one("#debug-panel")
            assert "visible" not in panel.classes

            # Toggle on
            await _pilot.press("~")
            await _pilot.pause()
            assert "visible" in panel.classes

            # Toggle off
            await _pilot.press("~")
            await _pilot.pause()
            assert "visible" not in panel.classes

    async def test_write_debug_log(self):
        """Test that _write_debug_log appends to the debug RichLog."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            # Make the panel visible so RichLog knows its size and renders immediately
            app.action_toggle_debug()
            await _pilot.pause()
            log = app.query_one("#debug-log", RichLog)
            initial = len(log.lines)
            app._write_debug_log("test log message")
            await _pilot.pause()
            assert len(log.lines) > initial

    async def test_log_callback_registered(self):
        """Test that the log callback is set on LaunchpadQueue during mount."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            assert lp._log_callback is not None
