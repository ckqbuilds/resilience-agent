import React from 'react';
import { Box, Text } from 'ink';

export function Footer() {
  return (
    <Box
      borderStyle="single"
      borderTop={true}
      paddingX={1}
      justifyContent="space-between"
    >
      <Text color="gray">/help</Text>
      <Text color="gray">/info</Text>
      <Text color="gray">/clear</Text>
      <Text color="gray">/quit</Text>
    </Box>
  );
}
