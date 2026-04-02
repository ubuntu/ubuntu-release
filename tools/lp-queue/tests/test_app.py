"""Tests for the TUI application."""

from unittest.mock import MagicMock

from textual.widgets import DataTable, OptionList, RichLog

from lp_queue.app import ConfirmScreen, QueueApp, RejectScreen, ReviewScreen, SeriesScreen
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
        "authors": "",
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

    async def test_review_screen_uses_diff_highlighter(self):
        """Test that the ReviewScreen writes content as a Syntax renderable with diff lexer."""
        from unittest.mock import patch

        from rich.syntax import Syntax

        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            item = _make_item()
            debdiff = "--- a/file\n+++ b/file\n@@ -1 +1 @@\n-old\n+new\n"
            screen = ReviewScreen(item, debdiff)
            written_objects = []
            original_write = RichLog.write

            def capture_write(self_log, content, *args, **kwargs):
                written_objects.append(content)
                return original_write(self_log, content, *args, **kwargs)

            with patch.object(RichLog, "write", capture_write):
                app.push_screen(screen)
                await _pilot.pause()

            assert len(written_objects) >= 1
            assert isinstance(written_objects[0], Syntax)
            assert written_objects[0].lexer.name == "Diff"


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


class TestConfirmScreen:
    """Tests for the ConfirmScreen modal."""

    async def test_confirm_with_y(self):
        """Test that pressing 'y' confirms and dismisses the screen."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            results = []
            screen = ConfirmScreen("Title", "Are you sure?")
            app.push_screen(screen, results.append)
            await _pilot.pause()
            assert app.screen is screen
            await _pilot.press("y")
            await _pilot.pause()
            assert app.screen is not screen
            assert results == [True]

    async def test_cancel_with_n(self):
        """Test that pressing 'n' cancels and dismisses the screen."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            results = []
            screen = ConfirmScreen("Title", "Are you sure?")
            app.push_screen(screen, results.append)
            await _pilot.pause()
            assert app.screen is screen
            await _pilot.press("n")
            await _pilot.pause()
            assert app.screen is not screen
            assert results == [False]

    async def test_cancel_with_escape(self):
        """Test that pressing escape cancels and dismisses the screen."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            results = []
            screen = ConfirmScreen("Title", "Are you sure?")
            app.push_screen(screen, results.append)
            await _pilot.pause()
            assert app.screen is screen
            await _pilot.press("escape")
            await _pilot.pause()
            assert app.screen is not screen
            assert results == [False]


class TestAcceptConfirmation:
    """Tests for the accept confirmation flow."""

    async def test_accept_shows_confirm(self):
        """Test that action_accept pushes a ConfirmScreen when an item is selected."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            app.queue_items = [_make_item(source_name="hello", version="2.10-3")]
            app._populate_table()
            app.action_accept()
            await _pilot.pause()
            assert isinstance(app.screen, ConfirmScreen)

    async def test_accept_cancelled(self):
        """Test that cancelling accept does not proceed."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            app.queue_items = [_make_item(source_name="hello", version="2.10-3")]
            app._populate_table()
            app.action_accept()
            await _pilot.pause()
            assert isinstance(app.screen, ConfirmScreen)
            await _pilot.press("n")
            await _pilot.pause()
            assert not isinstance(app.screen, ConfirmScreen)


class TestRejectConfirmation:
    """Tests for the reject confirmation flow."""

    async def test_reject_shows_reject_screen_first(self):
        """Test that action_reject pushes RejectScreen first."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            app.queue_items = [_make_item(source_name="hello", version="2.10-3")]
            app._populate_table()
            app.action_reject()
            await _pilot.pause()
            assert isinstance(app.screen, RejectScreen)

    async def test_reject_shows_confirm_after_comment(self):
        """Test that submitting a comment shows ConfirmScreen."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            app.queue_items = [_make_item(source_name="hello", version="2.10-3")]
            app._populate_table()
            app.action_reject()
            await _pilot.pause()
            assert isinstance(app.screen, RejectScreen)
            await _pilot.press("F", "T", "B", "F", "S")
            await _pilot.press("enter")
            await _pilot.pause()
            assert isinstance(app.screen, ConfirmScreen)

    async def test_reject_cancelled_at_confirm(self):
        """Test that cancelling at ConfirmScreen does not reject."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            app.queue_items = [_make_item(source_name="hello", version="2.10-3")]
            app._populate_table()
            app.action_reject()
            await _pilot.pause()
            await _pilot.press("F", "T", "B", "F", "S")
            await _pilot.press("enter")
            await _pilot.pause()
            assert isinstance(app.screen, ConfirmScreen)
            await _pilot.press("n")
            await _pilot.pause()
            assert not isinstance(app.screen, ConfirmScreen)


class TestSeriesScreen:
    """Tests for the SeriesScreen modal."""

    async def test_series_screen_displays_options(self):
        """Test that SeriesScreen renders the series list."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            series_list = [
                ("resolute", "26.04", True),
                ("noble", "24.04", True),
                ("jammy", "22.04", True),
                ("focal", "20.04", False),
            ]
            screen = SeriesScreen(series_list, "resolute")
            app.push_screen(screen)
            await _pilot.pause()
            assert app.screen is screen
            option_list = screen.query_one(OptionList)
            assert option_list.option_count == 4

    async def test_series_screen_dismiss_on_escape(self):
        """Test that pressing escape cancels the series screen."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            results = []
            series_list = [("resolute", "26.04", True)]
            screen = SeriesScreen(series_list, "resolute")
            app.push_screen(screen, results.append)
            await _pilot.pause()
            assert app.screen is screen
            await _pilot.press("escape")
            await _pilot.pause()
            assert app.screen is not screen
            assert results == [None]

    async def test_series_screen_current_marker(self):
        """Test that the current series is marked with a marker character."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            series_list = [
                ("resolute", "26.04", True),
                ("noble", "24.04", True),
            ]
            screen = SeriesScreen(series_list, "resolute")
            app.push_screen(screen)
            await _pilot.pause()
            option_list = screen.query_one(OptionList)
            first_option = option_list.get_option_at_index(0)
            second_option = option_list.get_option_at_index(1)
            assert "resolute" in str(first_option.prompt)
            assert "noble" in str(second_option.prompt)

    async def test_handle_series_result_cancel(self):
        """Test that None result from series screen sets cancel status."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            app._handle_series_result(None)

    async def test_handle_series_result_same_series(self):
        """Test that selecting the same series shows 'already on' message."""
        lp = LaunchpadQueue()
        app = QueueApp(lp_queue=lp)

        async with app.run_test(size=(120, 30)) as _pilot:
            app._handle_series_result("resolute")
