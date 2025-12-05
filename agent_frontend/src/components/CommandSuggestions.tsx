import React from 'react';
import { Box, Text } from 'ink';

interface Command {
  name: string;
  description: string;
}

interface CommandSuggestionsProps {
  input: string;
  commands: Command[];
}

export function CommandSuggestions({ input, commands }: CommandSuggestionsProps) {
  // Only show suggestions if input starts with /
  if (!input.startsWith('/')) {
    return null;
  }

  // Get the search term (everything after the /)
  const searchTerm = input.slice(1).toLowerCase();

  // Filter commands based on search term
  const filteredCommands = commands.filter((cmd) =>
    cmd.name.toLowerCase().startsWith(searchTerm)
  );

  // Don't show if no matches or if exact match
  if (filteredCommands.length === 0 ||
      (filteredCommands.length === 1 && filteredCommands[0].name === searchTerm)) {
    return null;
  }

  return (
    <Box flexDirection="column" marginLeft={2} marginBottom={1}>
      {filteredCommands.map((cmd) => (
        <Box key={cmd.name} marginY={0}>
          <Text color="cyan">/{cmd.name}</Text>
          <Text color="gray"> - {cmd.description}</Text>
        </Box>
      ))}
    </Box>
  );
}
