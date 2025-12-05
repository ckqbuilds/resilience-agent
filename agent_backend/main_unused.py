from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static, ProgressBar, Label, Collapsible
from textual.containers import Container, Vertical, Horizontal, Grid, ScrollableContainer
from textual.binding import Binding
from textual.screen import Screen
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
import boto3
import asyncio

from resilience_agent.agent import resilience_agent

# Initialize AWS clients
sts = boto3.client('sts')
session = boto3.Session()


class WorkingSection(Container):
    """Collapsible section showing agent's working process."""

    DEFAULT_CSS = """
    WorkingSection {
        height: auto;
        margin: 0 0 1 0;
    }

    WorkingSection Collapsible {
        background: $panel;
        border: solid $primary-darken-2;
        height: auto;
    }

    WorkingSection RichLog {
        height: auto;
        max-height: 20;
        background: $panel;
        border: none;
        padding: 0 1;
    }

    WorkingSection .working-title {
        color: $warning;
    }

    WorkingSection .completed-title {
        color: $success;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.working_log = RichLog(highlight=True, markup=True, wrap=True)
        self.collapsible = Collapsible(
            self.working_log,
            title="⟳ Working...",
            collapsed=False,
            classes="working-title"
        )

    def compose(self) -> ComposeResult:
        yield self.collapsible

    def add_text(self, text: str) -> None:
        """Add text to the working log."""
        self.working_log.write(text)

    def add_tool_call(self, tool_name: str, tool_input: dict = None) -> None:
        """Add a tool call to the working log."""
        # Highlight sub-agent invocations
        if tool_name in ["discovery_agent", "aws_knowledge_agent", "iac_agent"]:
            self.working_log.write(f"[bold cyan]→ Invoking {tool_name}[/bold cyan]")
            if tool_input and 'query' in tool_input:
                self.working_log.write(f"  [dim]{tool_input['query']}[/dim]")
        else:
            self.working_log.write(f"[dim]• Using tool: {tool_name}[/dim]")

    def add_tool_result(self, result: str) -> None:
        """Add a tool result to the working log."""
        # Truncate very long results
        if len(result) > 200:
            result = result[:200] + "..."
        self.working_log.write(f"[dim]  ✓ {result}[/dim]")

    def mark_complete(self) -> None:
        """Mark the working section as complete and collapse it."""
        self.collapsible.title = "✓ Completed"
        self.collapsible.remove_class("working-title")
        self.collapsible.add_class("completed-title")
        self.collapsible.collapsed = True


class ConversationMessage(Container):
    """Widget representing a single conversation turn (user message + agent response)."""

    DEFAULT_CSS = """
    ConversationMessage {
        height: auto;
        padding: 1;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary-darken-3;
    }

    ConversationMessage .user-message {
        color: $accent;
        text-style: bold;
        margin: 0 0 1 0;
    }

    ConversationMessage .assistant-response {
        color: $text;
        padding: 1 0 0 2;
    }
    """

    def __init__(self, user_message: str, **kwargs):
        super().__init__(**kwargs)
        self.user_message = user_message
        self.working_section = WorkingSection()
        self.response_widget = Static("", classes="assistant-response")

    def compose(self) -> ComposeResult:
        yield Static(f"[bold cyan]You:[/bold cyan] {self.user_message}", classes="user-message")
        yield self.working_section
        yield self.response_widget

    def update_working(self, text: str) -> None:
        """Add text to the working section."""
        self.working_section.add_text(text)

    def add_tool_call(self, tool_name: str, tool_input: dict = None) -> None:
        """Add a tool call to the working section."""
        self.working_section.add_tool_call(tool_name, tool_input)

    def add_tool_result(self, result: str) -> None:
        """Add a tool result to the working section."""
        self.working_section.add_tool_result(result)

    def set_response(self, response: str) -> None:
        """Set the final response text."""
        self.response_widget.update(f"[bold green]Assistant:[/bold green]\n{response}")
        self.working_section.mark_complete()


class ConversationView(ScrollableContainer):
    """Scrollable container for conversation messages."""

    DEFAULT_CSS = """
    ConversationView {
        height: 1fr;
        background: $background;
        padding: 1;
    }

    ConversationView:focus {
        border: none;
    }
    """

    def add_message(self, message: ConversationMessage) -> None:
        """Add a new conversation message."""
        self.mount(message)
        # Scroll to bottom
        self.scroll_end(animate=False)


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
    """A TUI that mimics Claude Code's terminal aesthetic with streaming support."""

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
        yield ConversationView()
        yield InputArea()
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app when mounted."""
        self.title = "Resilience Architect"

        # Add welcome message
        conversation_view = self.query_one(ConversationView)
        welcome = Static(
            "[bold cyan]Welcome to Resilience Architect![/bold cyan]\n"
            "[dim]Type your message and press Enter to send.[/dim]\n",
            classes="user-message"
        )
        conversation_view.mount(welcome)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle when user submits input."""
        message = event.value.strip()

        if not message:
            return

        # Get input widget and clear it
        input_widget = self.query_one(Input)
        input_widget.value = ""

        # Create new conversation message widget
        conversation_view = self.query_one(ConversationView)
        message_widget = ConversationMessage(message)
        conversation_view.add_message(message_widget)

        # Start streaming response
        asyncio.create_task(self.stream_agent_response(message_widget, message))

    async def stream_agent_response(self, message_widget: ConversationMessage, user_message: str) -> None:
        """Stream the agent's response using stream_async()."""
        accumulated_response = []
        
        try:
            # Stream events from the agent
            async for event in resilience_agent.stream_async(user_message):
                if not isinstance(event, dict):
                    continue
                
                # Text chunks have 'data' key with the text
                if 'data' in event and isinstance(event['data'], str):
                    chunk = event['data']
                    accumulated_response.append(chunk)
                    # Show streaming text in working section
                    message_widget.update_working(chunk)
                
                # Tool use events
                elif 'current_tool_use' in event:
                    tool_use = event['current_tool_use']
                    # Handle both dict and string formats
                    if isinstance(tool_use, dict):
                        tool_name = tool_use.get('name', 'unknown')
                        tool_input = tool_use.get('input', {})
                    elif isinstance(tool_use, str):
                        tool_name = tool_use
                        tool_input = {}
                    else:
                        tool_name = str(tool_use)
                        tool_input = {}
                    message_widget.add_tool_call(tool_name, tool_input)
                
                # Tool result events
                elif 'tool_result' in event:
                    result = event['tool_result']
                    # Handle different result formats
                    if isinstance(result, dict):
                        result_content = str(result.get('content', ''))[:100]
                    else:
                        result_content = str(result)[:100]
                    if result_content:
                        message_widget.add_tool_result(result_content)
                
                # Final result with complete message
                elif 'result' in event:
                    # This is the final AgentResult object
                    pass  # We've already accumulated the text chunks
            
            # Set final response
            final_response = "".join(accumulated_response)
            if final_response:
                message_widget.set_response(final_response)
            else:
                message_widget.set_response("[dim]No response generated[/dim]")
                
        except Exception as e:
            # Handle errors gracefully
            error_message = f"[red]Error: {str(e)}[/red]"
            message_widget.set_response(error_message)
            message_widget.working_section.mark_complete()

    def action_clear(self) -> None:
        """Clear the conversation view."""
        conversation_view = self.query_one(ConversationView)
        # Remove all children
        conversation_view.remove_children()
        # Add cleared message
        cleared = Static("[dim]Conversation cleared.[/dim]\n", classes="user-message")
        conversation_view.mount(cleared)

    def action_show_info(self) -> None:
        """Show the LLM info and progress screen."""
        self.push_screen(LLMInfoScreen())

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


if __name__ == "__main__":
    app = ResilienceCli()
    app.run()
