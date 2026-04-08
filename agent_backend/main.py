from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static, ProgressBar, Label, Button
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from rich.syntax import Syntax
from rich.table import Table
import boto3
import argparse

from resilience_agent.agent import resilience_agent, mode_state

# Initialize AWS clients
sts = boto3.client('sts')
session = boto3.Session()


class MessageDisplay(RichLog):
    """Custom widget for displaying chat messages."""

    DEFAULT_CSS = """
    MessageDisplay {
        background: $surface;
        border: solid $primary;
        height: 1fr;
        padding: 1;
    }
    """


class ModeTransitionDialog(ModalScreen[bool]):
    """Modal dialog for approving mode transitions."""

    DEFAULT_CSS = """
    ModeTransitionDialog {
        align: center middle;
    }

    ModeTransitionDialog > Vertical {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $warning;
        padding: 2;
    }

    .dialog-title {
        text-style: bold;
        color: $warning;
        text-align: center;
        margin-bottom: 1;
    }

    .dialog-content {
        margin: 1 0;
    }

    .dialog-buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    .approve-button {
        background: $success;
        color: $text;
        margin: 0 1;
    }

    .reject-button {
        background: $error;
        color: $text;
        margin: 0 1;
    }
    """

    def __init__(self, current_mode: str, required_mode: str, tool_name: str, reason: str):
        super().__init__()
        self.current_mode = current_mode
        self.required_mode = required_mode
        self.tool_name = tool_name
        self.reason = reason

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("⚠️ MODE TRANSITION REQUIRED ⚠️", classes="dialog-title")
            yield Static(
                f"\nThe agent wants to use tool: [bold]{self.tool_name}[/bold]\n\n"
                f"Current Mode: [green]{self.current_mode}[/green]\n"
                f"Required Mode: [yellow]{self.required_mode}[/yellow]\n\n"
                f"Reason: {self.reason}\n\n"
                f"Do you approve switching to {self.required_mode} mode?",
                classes="dialog-content"
            )
            with Horizontal(classes="dialog-buttons"):
                yield Button("Approve (Y)", variant="success", id="approve")
                yield Button("Reject (N)", variant="error", id="reject")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "approve":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "y":
            self.dismiss(True)
        elif event.key == "n":
            self.dismiss(False)
        elif event.key == "escape":
            self.dismiss(False)


class LLMInfoScreen(Screen):
    """Screen showing LLM info, progress, and AWS details."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("i", "dismiss", "Close", show=True),
    ]

    DEFAULT_CSS = """
    LLMInfoScreen {
        align: center middle;
    }

    LLMInfoScreen > Vertical {
        width: 80;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 2;
    }

    .info-section {
        height: auto;
        border: solid $accent;
        padding: 1;
        margin: 1 0;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .info-grid {
        height: auto;
        grid-size: 2;
        grid-gutter: 1;
        margin: 1 0;
    }

    .info-label {
        color: $text-muted;
        text-style: bold;
    }

    .info-value {
        color: $text;
    }

    ProgressBar {
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("[bold]LLM Information & Progress[/bold]", classes="section-title")

            # Operation Mode Section (NEW)
            with Container(classes="info-section"):
                yield Static("[bold cyan]Operation Mode[/bold cyan]", classes="section-title")
                mode = mode_state.current_mode
                with Grid(classes="info-grid"):
                    yield Static("Current Mode:", classes="info-label")
                    yield Static(
                        f"[{mode.color}]{mode.name}[/{mode.color}] - {mode.description}",
                        classes="info-value"
                    )
                    yield Static("Mode History:", classes="info-label")
                    history_text = ""
                    for transition in mode_state._mode_history[-3:]:  # Last 3 transitions
                        history_text += (f"{transition.from_mode.name} → "
                                       f"{transition.to_mode.name} "
                                       f"({transition.timestamp.strftime('%H:%M:%S')})\n")
                    yield Static(history_text or "No transitions yet", classes="info-value")

            # Model Information Section
            with Container(classes="info-section"):
                yield Static("[bold cyan]Model Information[/bold cyan]", classes="section-title")
                with Grid(classes="info-grid"):
                    yield Static("Model:", classes="info-label")
                    yield Static(f"{resilience_agent.model.get_config().get('model_id')}", classes="info-value")
                    yield Static("Max Tokens:", classes="info-label")
                    yield Static(f"{resilience_agent.model.get_config().get('max_tokens')}", classes="info-value")
                    yield Static("Temperature:", classes="info-label")
                    yield Static(f"{resilience_agent.model.get_config().get('params')}", classes="info-value")
                    yield Static("Tools:", classes="info-label")
                    yield Static(f"{resilience_agent.tool_names}", classes="info-value")


            # Context Usage Section
            with Container(classes="info-section"):
                yield Static("[bold cyan]Context Usage[/bold cyan]", classes="section-title")
                yield Static("Tokens Used: 45,231 / 200,000", classes="info-value")
                yield ProgressBar(total=100, show_eta=False)
                yield Static("[dim]22.6% of context window used[/dim]")

            # AWS Configuration Section
            with Container(classes="info-section"):
                yield Static("[bold cyan]AWS Configuration[/bold cyan]", classes="section-title")
                with Grid(classes="info-grid"):
                    yield Static("Region:", classes="info-label")
                    yield Static(f"{session.region_name}", classes="info-value")
                    yield Static("Profile:", classes="info-label")
                    yield Static(f"{session.profile_name}", classes="info-value")
                    yield Static("Account ID:", classes="info-label")
                    yield Static(f"{sts.get_caller_identity().get('Account')}", classes="info-value")

            # Request Statistics Section
            with Container(classes="info-section"):
                yield Static("[bold cyan]Session Statistics[/bold cyan]", classes="section-title")
                with Grid(classes="info-grid"):
                    yield Static("Total Requests:", classes="info-label")
                    yield Static("42", classes="info-value")
                    yield Static("Avg Response Time:", classes="info-label")
                    yield Static("2.3s", classes="info-value")
                    yield Static("Total Cost:", classes="info-label")
                    yield Static("$0.23", classes="info-value")
                    yield Static("Session Duration:", classes="info-label")
                    yield Static("00:15:42", classes="info-value")

            yield Static("\n[dim]Press 'i' or 'ESC' to close[/dim]", classes="info-value")

    def on_mount(self) -> None:
        """Initialize progress bar with current value."""
        progress_bar = self.query_one(ProgressBar)
        # Set to 22.6% to match the dummy data (45,231 / 200,000)
        progress_bar.update(progress=22.6)

    async def action_dismiss(self, result=None) -> None:
        """Close the info screen."""
        self.app.pop_screen()


class InputArea(Container):
    """Custom container for the input area."""

    DEFAULT_CSS = """
    InputArea {
        height: auto;
        padding: 1;
        background: $surface;
        border-top: solid $primary;
    }

    InputArea Input {
        border: none;
        background: $panel;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Type your message... (Press Enter to send)")


class ResilienceCli(App):
    """A TUI that mimics Claude Code's terminal aesthetic."""

    CSS = """
    Screen {
        background: $background;
    }

    Header {
        background: $primary;
        color: $text;
        text-style: bold;
    }

    Footer {
        background: $panel;
    }

    .message-user {
        color: $accent;
        text-style: bold;
    }

    .message-assistant {
        color: $success;
    }
    """

    BINDINGS = [
        Binding("i", "show_info", "Info", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+l", "clear", "Clear", show=True),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield MessageDisplay(highlight=True, markup=True, wrap=True)
        yield InputArea()
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app when mounted."""
        # Reset to planning mode on startup
        mode_state.reset_to_planning()

        self.title = "Resilience Architect"
        self.update_subtitle()

        # Get the message display and show welcome message
        message_display = self.query_one(MessageDisplay)
        message_display.write("Hello from the Resilience Architect!")
        message_display.write(f"[dim]Current Mode: {mode_state.current_mode.name}[/dim]")
        message_display.write("[dim]Type your message and press Enter to send.[/dim]\n")

    def update_subtitle(self) -> None:
        """Update the subtitle with current mode."""
        mode = mode_state.current_mode
        color = mode.color
        self.sub_title = f"[{color}]Mode: {mode.name}[/{color}]"

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle when user submits input."""
        message = event.value.strip()

        if not message:
            return

        # Get widgets
        message_display = self.query_one(MessageDisplay)
        input_widget = self.query_one(Input)

        # Display user message
        message_display.write(f"[bold cyan]You:[/bold cyan] {message}")

        # Get assistant response
        self.get_assistant_response(message_display, message)

        # Clear input
        input_widget.value = ""

    def get_assistant_response(self, display: MessageDisplay, user_message: str) -> None:
        """Get response from the agent with interrupt handling."""

        def update_display(response):
            # Check if we got an interrupt
            if hasattr(response, 'stop_reason') and hasattr(response, 'interrupts') and response.interrupts:
                self.handle_interrupts(response, display, user_message)
            else:
                # Normal response
                try:
                    # Extract text from response message
                    if hasattr(response, 'message'):
                        if isinstance(response.message, dict) and 'content' in response.message:
                            text_parts = []
                            for content_block in response.message['content']:
                                if isinstance(content_block, dict) and 'text' in content_block:
                                    text_parts.append(content_block['text'])
                            text_response = '\n'.join(text_parts) if text_parts else str(response.message)
                        else:
                            text_response = str(response.message)
                    else:
                        text_response = str(response)
                except (KeyError, IndexError, TypeError):
                    text_response = str(response)

                display.write(f"[bold green]Assistant:[/bold green] {text_response}")
                display.write("")

        def run_agent():
            response = resilience_agent(user_message)
            self.call_from_thread(update_display, response)

        self.run_worker(run_agent, exclusive=True, thread=True)

    def handle_interrupts(self, result, display: MessageDisplay, original_message: str) -> None:
        """Handle interrupts from the agent (mode transitions, etc.)."""
        interrupts = result.interrupts

        for interrupt in interrupts:
            if interrupt.reason.get("type") == "mode_transition_required":
                # Show modal dialog for approval
                self.handle_mode_transition_interrupt(interrupt, display, original_message)
                break

    def handle_mode_transition_interrupt(self, interrupt, display: MessageDisplay,
                                        original_message: str) -> None:
        """Handle mode transition interrupt with modal dialog."""
        reason_data = interrupt.reason
        current_mode = reason_data["current_mode"]
        required_mode = reason_data["required_mode"]
        tool_name = reason_data["tool_name"]
        message = reason_data["message"]

        # This needs to be async to use push_screen_wait
        async def show_dialog_and_resume():
            # Show modal dialog
            dialog = ModeTransitionDialog(current_mode, required_mode, tool_name, message)
            approved = await self.push_screen_wait(dialog)

            # Create interrupt response
            response_content = {
                "interruptResponse": {
                    "interruptId": interrupt.id,
                    "response": {"approved": approved}
                }
            }

            if approved:
                display.write(f"[yellow]Mode transition to {required_mode} approved.[/yellow]")
                self.update_subtitle()  # Update header
            else:
                display.write(f"[red]Mode transition to {required_mode} rejected.[/red]")

            # Resume agent with response
            def resume_agent():
                result = resilience_agent([response_content])

                def show_result(r):
                    try:
                        # Extract text from response
                        if hasattr(r, 'message'):
                            if isinstance(r.message, dict) and 'content' in r.message:
                                text_parts = []
                                for content_block in r.message['content']:
                                    if isinstance(content_block, dict) and 'text' in content_block:
                                        text_parts.append(content_block['text'])
                                text_response = '\n'.join(text_parts) if text_parts else str(r.message)
                            else:
                                text_response = str(r.message)
                        else:
                            text_response = str(r)
                    except (KeyError, IndexError, TypeError):
                        text_response = str(r)

                    display.write(f"[bold green]Assistant:[/bold green] {text_response}")
                    display.write("")
                    # Update subtitle again in case mode changed
                    self.update_subtitle()

                self.call_from_thread(show_result, result)

            self.run_worker(resume_agent, exclusive=True, thread=True)

        # Run the async dialog
        self.run_worker(show_dialog_and_resume, exclusive=True)

    def action_clear(self) -> None:
        """Clear the message display."""
        message_display = self.query_one(MessageDisplay)
        message_display.clear()
        message_display.write("[dim]Chat cleared.[/dim]\n")

    def action_show_info(self) -> None:
        """Show the LLM info and progress screen."""
        self.push_screen(LLMInfoScreen())

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Resilience Architect - AWS FIS Chaos Engineering Assistant")
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Run in read-only mode (locks to Planning mode, prevents mode transitions)"
    )
    args = parser.parse_args()

    # Update the operation mode hook with read_only flag
    if args.read_only:
        from resilience_agent.agent import operation_mode_hook
        operation_mode_hook.read_only = True
        print("[INFO] Running in READ-ONLY mode - mode transitions are disabled")

    app = ResilienceCli()
    app.run()