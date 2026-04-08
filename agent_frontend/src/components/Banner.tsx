import React from 'react';
import { Box, Text } from 'ink';
import BigText from 'ink-big-text';
import Gradient from 'ink-gradient';

export function Banner() {
  return (
    <Box flexDirection="column" marginBottom={1}>
      {/* <Gradient name="pastel"> */}
        <BigText text="Resilience Architect" font="block" />
      {/* </Gradient> */}
      <Box marginTop={1}>
        <Text color="gray">Tips for getting started:</Text>
      </Box>
      <Text color="gray">1. Ask questions, plan experiments, or run commands.</Text>
      <Text color="gray">2. Be specific for the best results.</Text>
      <Text color="gray">
        3. <Text color="cyan">/help</Text> for more information.
      </Text>
    </Box>
  );
}
