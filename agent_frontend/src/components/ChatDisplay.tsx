import React from 'react';
import { Box, Text } from 'ink';
import { format } from 'date-fns';
import type { Message } from '../types.js';

interface ChatDisplayProps {
  messages: Message[];
}

export function ChatDisplay({ messages }: ChatDisplayProps) {
  return (
    <Box flexDirection="column" paddingY={1}>
      {messages.map((message, index) => (
        <Box key={index} flexDirection="column" marginBottom={1}>
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
}
