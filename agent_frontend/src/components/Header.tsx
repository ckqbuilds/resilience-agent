import React from 'react';
import { Box, Text } from 'ink';

export function Header() {
  return (
    <Box
      borderStyle="single"
      borderBottom={true}
      paddingX={1}
      justifyContent="center"
    >
      <Text bold color="cyan">
        Resilience Architect
      </Text>
    </Box>
  );
}
