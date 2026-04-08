import { memo } from 'react';
import { Box, Text } from 'ink';
import type { Message } from '../types.js';
import { ActionLog } from './ActionLog.js';

interface ChatDisplayProps {
  messages: Message[];
}

export const ChatDisplay = memo(function ChatDisplay({ messages }: ChatDisplayProps) {
  return (
    <Box flexDirection="column" paddingY={1}>
      {messages.map((message) => (
        <Box key={message.timestamp.getTime()} flexDirection="column" marginBottom={1}>
          {/* Show action log for assistant messages with events */}
          {message.role === 'assistant' && message.events && (
            <ActionLog events={message.events} />
          )}

          {message.role === 'user' && (
            <Box>
              <Text bold color="cyan">
                You:
              </Text>
              <Text> {message.content}</Text>
            </Box>
          )}
          {message.role === 'assistant' && (
            <Box flexDirection="column">
              <Text bold color="green">
                Assistant:
              </Text>
              <Text>{message.content}</Text>
            </Box>
          )}
          {message.role === 'system' && (
            <Text color="gray" dimColor>
              {message.content}
            </Text>
          )}
        </Box>
      ))}
    </Box>
  );
});
