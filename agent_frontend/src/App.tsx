import { useState, useEffect, useMemo } from 'react';
import { Box, Text, useInput, useApp } from 'ink';
import TextInput from 'ink-text-input';
import Spinner from 'ink-spinner';
import { ChatDisplay } from './components/ChatDisplay.js';
import { InfoScreen } from './components/InfoScreen.js';
import { ModeTransitionDialog } from './components/ModeTransitionDialog.js';
import { CommandSuggestions } from './components/CommandSuggestions.js';
import { Banner } from './components/Banner.js';
import { Header } from './components/Header.js';
import { Footer } from './components/Footer.js';
import { AgentService } from './services/AgentService.js';
import type { Message, ModeState } from './types.js';

const AVAILABLE_COMMANDS = [
  { name: 'help', description: 'Display available commands' },
  { name: 'info', description: 'Show LLM model info, AWS config, and session statistics' },
  { name: 'clear', description: 'Clear chat history' },
  { name: 'mode', description: 'Display current operation mode' },
  { name: 'quit', description: 'Exit the application' },
  { name: 'exit', description: 'Exit the application' },
];

export function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const [modeState, setModeState] = useState<ModeState>({
    current: 'Planning',
    color: 'yellow',
    description: 'Planning chaos experiments',
  });
  const [showModeDialog, setShowModeDialog] = useState(false);
  const [pendingModeTransition, setPendingModeTransition] = useState<any>(null);
  const [showBanner, setShowBanner] = useState(true);

  const { exit } = useApp();
  // Use useMemo to create AgentService only once and keep the same session ID
  const agentService = useMemo(() => new AgentService(), []);

  // Hide banner when user sends first message
  useEffect(() => {
    if (messages.length > 0) {
      setShowBanner(false);
    }
  }, [messages]);

  // Handle slash commands
  const handleSlashCommand = async (command: string) => {
    const parts = command.slice(1).split(' ');
    const cmd = parts[0]?.toLowerCase() || '';

    switch (cmd) {
      case 'help':
        setMessages((prev) => [
          ...prev,
          {
            role: 'system',
            content:
              'Available commands:\n' +
              '/help - Show this help message\n' +
              '/info - Show LLM and AWS information\n' +
              '/clear - Clear chat history\n' +
              '/quit - Exit the application\n' +
              '/mode - Show current operation mode',
            timestamp: new Date(),
          },
        ]);
        break;

      case 'info':
        setShowInfo(true);
        break;

      case 'clear':
        setMessages([
          {
            role: 'system',
            content: 'Chat cleared.',
            timestamp: new Date(),
          },
        ]);
        break;

      case 'quit':
      case 'exit':
        exit();
        break;

      case 'mode':
        setMessages((prev) => [
          ...prev,
          {
            role: 'system',
            content: `Current Mode: ${modeState.current} - ${modeState.description}`,
            timestamp: new Date(),
          },
        ]);
        break;

      default:
        setMessages((prev) => [
          ...prev,
          {
            role: 'system',
            content: `Unknown command: /${cmd}. Type /help for available commands.`,
            timestamp: new Date(),
          },
        ]);
    }
  };

  const handleSubmit = async (value: string) => {
    if (!value.trim()) return;

    // Check if it's a slash command
    if (value.startsWith('/')) {
      await handleSlashCommand(value);
      setInput('');
      return;
    }

    // Add user message
    const userMessage: Message = {
      role: 'user',
      content: value,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Call the agent service
      const response = await agentService.sendMessage(value);

      // Check for mode transition interrupts
      if (response.interrupt) {
        setPendingModeTransition(response.interrupt);
        setShowModeDialog(true);
        setIsLoading(false);
        return;
      }

      // Add assistant response
      const assistantMessage: Message = {
        role: 'assistant',
        content: response.content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: 'system',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleModeApproval = async (approved: boolean) => {
    setShowModeDialog(false);

    if (approved && pendingModeTransition) {
      // Update mode state
      setModeState({
        current: pendingModeTransition.requiredMode,
        color: pendingModeTransition.color || 'yellow',
        description: pendingModeTransition.description || '',
      });

      setMessages((prev) => [
        ...prev,
        {
          role: 'system',
          content: `Mode transition to ${pendingModeTransition.requiredMode} approved.`,
          timestamp: new Date(),
        },
      ]);

      // Resume agent with approval
      try {
        const response = await agentService.respondToInterrupt(
          pendingModeTransition.id,
          approved
        );

        const assistantMessage: Message = {
          role: 'assistant',
          content: response.content,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (error) {
        const errorMessage: Message = {
          role: 'system',
          content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } else {
      setMessages((prev) => [
        ...prev,
        {
          role: 'system',
          content: `Mode transition to ${pendingModeTransition?.requiredMode} rejected.`,
          timestamp: new Date(),
        },
      ]);
    }

    setPendingModeTransition(null);
  };

  // Global key handlers
  useInput((_input, key) => {
    if (key.escape && showInfo) {
      setShowInfo(false);
    }
  });

  if (showModeDialog && pendingModeTransition) {
    return (
      <ModeTransitionDialog
        currentMode={modeState.current}
        requiredMode={pendingModeTransition.requiredMode}
        toolName={pendingModeTransition.toolName}
        reason={pendingModeTransition.reason}
        onApprove={() => handleModeApproval(true)}
        onReject={() => handleModeApproval(false)}
      />
    );
  }

  if (showInfo) {
    return (
      <InfoScreen
        modeState={modeState}
        onClose={() => setShowInfo(false)}
      />
    );
  }

  return (
    <Box flexDirection="column" height="100%">
      <Header mode={modeState} />

      <Box flexGrow={1} flexDirection="column" paddingX={1}>
        {showBanner && <Banner />}
        <ChatDisplay messages={messages} />
      </Box>

      <Box
        flexDirection="column"
        borderStyle="single"
        borderTop={true}
        paddingX={1}
        paddingY={0}
      >
        <CommandSuggestions input={input} commands={AVAILABLE_COMMANDS} />
        <Box>
          <Text color="cyan">› </Text>
          {isLoading || showModeDialog ? (
            <Box>
              <Spinner type="dots" />
              <Text>
                {' '}
                {showModeDialog
                  ? 'Waiting for mode approval...'
                  : 'Loading...'}
              </Text>
            </Box>
          ) : (
            <TextInput
              value={input}
              onChange={setInput}
              onSubmit={handleSubmit}
              placeholder="Type your message... (Press Enter to send, /help for commands)"
            />
          )}
        </Box>
      </Box>

      <Footer />
    </Box>
  );
}
