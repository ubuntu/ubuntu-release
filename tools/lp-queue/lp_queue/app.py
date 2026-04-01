"""TUI application for the Ubuntu Launchpad upload queue."""

from __future__ import annotations

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Input, Label, RichLog

from lp_queue.launchpad import LaunchpadQueue, QueueItem


class ReviewScreen(ModalScreen[None]):
    """Modal screen to display a debdiff for review."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    ReviewScreen {
        align: center middle;
    }

    ReviewScreen > Vertical {
        width: 90%;
        height: 90%;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    ReviewScreen RichLog {
        height: 1fr;
    }

    ReviewScreen .review-title {
        dock: top;
        text-style: bold;
        padding: 1;
        background: $accent;
        color: $text;
        width: 100%;
    }
    """

    def __init__(self, item: QueueItem, debdiff: str) -> None:
        super().__init__()
        self.item = item
        self.debdiff = debdiff

    def compose(self) -> ComposeResult:
        """Build the review screen layout."""
        with Vertical():
            yield Label(f"Review: {self.item.display_name}", classes="review-title")
            yield RichLog(highlight=True, markup=False)

    def on_mount(self) -> None:
        """Load the debdiff content into the log widget."""
        log = self.query_one(RichLog)
        log.write(self.debdiff)


class RejectScreen(ModalScreen[str | None]):
    """Modal screen to collect a rejection comment."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    RejectScreen {
        align: center middle;
    }

    RejectScreen > Vertical {
        width: 60%;
        height: auto;
        max-height: 50%;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }

    RejectScreen .reject-title {
        text-style: bold;
        padding: 1;
        background: $error;
        color: $text;
        width: 100%;
    }

    RejectScreen Input {
        margin: 1 0;
    }
    """

    def __init__(self, item: QueueItem) -> None:
        super().__init__()
        self.item = item

    def compose(self) -> ComposeResult:
        """Build the rejection comment input screen."""
        with Vertical():
            yield Label(f"Reject: {self.item.display_name}", classes="reject-title")
            yield Label("Enter rejection reason:")
            yield Input(placeholder="Reason for rejection...")

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle the rejection comment submission."""
        comment = event.value.strip()
        if comment:
            self.dismiss(comment)

    def action_cancel(self) -> None:
        """Cancel the rejection."""
        self.dismiss(None)


class QueueApp(App[None]):
    """TUI application for managing the Ubuntu upload queue."""

    TITLE = "Ubuntu Upload Queue"

    BINDINGS = [
        Binding("r", "review", "Review"),
        Binding("a", "accept", "Accept"),
        Binding("j", "reject", "Reject"),
        Binding("f5", "refresh", "Refresh"),
        Binding("tilde", "toggle_debug", "Debug", show=False),
        Binding("q", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    DataTable {
        height: 1fr;
    }

    #debug-panel {
        height: 12;
        border-top: thick $accent;
        background: $surface;
        display: none;
    }

    #debug-panel.visible {
        display: block;
    }

    .debug-title {
        dock: top;
        text-style: bold;
        padding: 0 1;
        background: $accent;
        color: $text;
        width: 100%;
        height: 1;
    }

    .status-bar {
        width: 100%;
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
    }

    .status-bar.busy {
        background: $warning;
        color: $text;
        text-style: bold;
    }

    .status-bar.error {
        background: $error;
        color: $text;
        text-style: bold;
    }

    .status-bar.success {
        background: $success;
        color: $text;
    }
    """

    def __init__(self, lp_queue: LaunchpadQueue | None = None) -> None:
        super().__init__()
        self.lp_queue = lp_queue or LaunchpadQueue()
        self.queue_items: list[QueueItem] = []
        self.username = ""

    def compose(self) -> ComposeResult:
        """Build the main application layout."""
        yield Header()
        yield DataTable()
        with Vertical(id="debug-panel"):
            yield Label("Launchpad Debug Log", classes="debug-title")
            yield RichLog(id="debug-log", highlight=True, markup=False)
        yield Label("⏳ Connecting to Launchpad…", classes="status-bar busy")
        yield Footer()

    def on_mount(self) -> None:
        """Set up the data table and load queue items."""
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns(
            "Package", "Version", "Component", "Section", "Status", "Sync", "Created"
        )
        self.lp_queue.set_log_callback(self._on_lp_log)
        self._connect_and_load()

    def _on_lp_log(self, message: str) -> None:
        """Receive a log message from LaunchpadQueue and write it to the debug panel."""
        self.app.call_from_thread(self._write_debug_log, message)

    def _write_debug_log(self, message: str) -> None:
        """Append a message to the debug RichLog widget."""
        self.query_one("#debug-log", RichLog).write(message)

    def action_toggle_debug(self) -> None:
        """Toggle visibility of the Launchpad debug log panel."""
        panel = self.query_one("#debug-panel")
        panel.toggle_class("visible")

    def _set_username(self, username):
        self.username = username

    def _set_status(self, message: str, state: str = "") -> None:
        """Update the status bar message and visual state.

        Args:
            message: The status text to display.
            state: Visual state — ``"busy"``, ``"error"``, ``"success"``, or
                ``""`` for the default/idle look.
        """
        bar = self.query_one(".status-bar", Label)
        bar.remove_class("busy", "error", "success")
        if state:
            bar.add_class(state)
        msg = message
        if self.username:
            msg = f"Connected as '{self.username}' - {message}"
        bar.update(msg)

    def _get_selected_item(self) -> QueueItem | None:
        """Return the currently selected queue item, or None."""
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        row_idx = table.cursor_row
        if 0 <= row_idx < len(self.queue_items):
            return self.queue_items[row_idx]
        return None

    @work(thread=True)
    def _connect_and_load(self) -> None:
        """Connect to Launchpad and load the queue (runs in a worker thread)."""
        try:
            self.app.call_from_thread(self._set_status, "⏳ Connecting to Launchpad…", "busy")
            self.lp_queue.connect()
            self.app.call_from_thread(self._set_status, "⏳ Getting user name…", "busy")
            self.app.call_from_thread(self._set_username, self.lp_queue.lp_user_name())
            self.app.call_from_thread(self._set_status, "⏳ Loading queue items…", "busy")
            self.queue_items = self.lp_queue.get_queue_items()
            self.app.call_from_thread(self._populate_table)
        except Exception as exc:
            self.app.call_from_thread(self._set_status, f"❌ Error: {exc}", "error")

    @work(thread=True)
    def _load_queue(self) -> None:
        """Refresh queue items from Launchpad (runs in a worker thread)."""
        try:
            self.app.call_from_thread(self._set_status, "⏳ Refreshing queue…", "busy")
            self.queue_items = self.lp_queue.get_queue_items()
            self.app.call_from_thread(self._populate_table)
        except Exception as exc:
            self.app.call_from_thread(self._set_status, f"❌ Error: {exc}", "error")

    def _populate_table(self) -> None:
        """Populate the data table with current queue items."""
        table = self.query_one(DataTable)
        table.clear()
        for item in self.queue_items:
            table.add_row(
                item.source_name,
                item.version,
                item.component,
                item.section,
                item.status,
                "Yes" if item.is_sync else "No",
                item.date_created,
            )
        self._set_status(f"{len(self.queue_items)} items in queue")

    def action_refresh(self) -> None:
        """Refresh the queue listing."""
        self._load_queue()

    def action_review(self) -> None:
        """Review the selected queue item by showing its debdiff."""
        item = self._get_selected_item()
        if item is None:
            self._set_status("No item selected")
            return
        self._fetch_debdiff(item)

    @work(thread=True)
    def _fetch_debdiff(self, item: QueueItem) -> None:
        """Fetch the debdiff in a worker thread and push the review screen."""
        self.app.call_from_thread(
            self._set_status, f"⏳ Fetching debdiff for {item.display_name}…", "busy"
        )
        try:
            debdiff = self.lp_queue.get_debdiff(item)
            self.app.call_from_thread(self.push_screen, ReviewScreen(item, debdiff))
            self.app.call_from_thread(
                self._set_status, f"Reviewing {item.display_name}"
            )
        except Exception as exc:
            self.app.call_from_thread(self._set_status, f"❌ Error: {exc}", "error")

    def action_accept(self) -> None:
        """Accept the selected queue item."""
        item = self._get_selected_item()
        if item is None:
            self._set_status("No item selected")
            return
        self._do_accept(item)

    @work(thread=True)
    def _do_accept(self, item: QueueItem) -> None:
        """Accept the item in a worker thread."""
        self.app.call_from_thread(
            self._set_status, f"⏳ Accepting {item.display_name}…", "busy"
        )
        try:
            self.lp_queue.accept(item)
            self.app.call_from_thread(
                self._set_status, f"✔ Accepted {item.display_name}", "success"
            )
            self.queue_items = self.lp_queue.get_queue_items()
            self.app.call_from_thread(self._populate_table)
        except Exception as exc:
            self.app.call_from_thread(self._set_status, f"❌ Error: {exc}", "error")

    def action_reject(self) -> None:
        """Reject the selected queue item, asking for a comment."""
        item = self._get_selected_item()
        if item is None:
            self._set_status("No item selected")
            return
        self.push_screen(RejectScreen(item), self._handle_reject_result)

    def _handle_reject_result(self, comment: str | None) -> None:
        """Process the result from the reject screen."""
        if comment is None:
            self._set_status("Rejection cancelled")
            return
        item = self._get_selected_item()
        if item is None:
            return
        self._do_reject(item, comment)

    @work(thread=True)
    def _do_reject(self, item: QueueItem, comment: str) -> None:
        """Reject the item in a worker thread."""
        self.app.call_from_thread(
            self._set_status, f"⏳ Rejecting {item.display_name}…", "busy"
        )
        try:
            self.lp_queue.reject(item, comment)
            self.app.call_from_thread(
                self._set_status, f"✔ Rejected {item.display_name}", "success"
            )
            self.queue_items = self.lp_queue.get_queue_items()
            self.app.call_from_thread(self._populate_table)
        except Exception as exc:
            self.app.call_from_thread(self._set_status, f"❌ Error: {exc}", "error")


def main() -> None:
    """Run the TUI application."""
    app = QueueApp()
    app.run()


if __name__ == "__main__":
    main()
