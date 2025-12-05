import React from 'react';
import { Box, Text, useInput } from 'ink';

interface ModeTransitionDialogProps {
  currentMode: string;
  requiredMode: string;
  toolName: string;
  reason: string;
  onApprove: () => void;
  onReject: () => void;
}

export function ModeTransitionDialog({
  currentMode,
  requiredMode,
  toolName,
  reason,
  onApprove,
  onReject,
}: ModeTransitionDialogProps) {
  useInput((input, key) => {
    if (input === 'y' || input === 'Y') {
      onApprove();
    } else if (input === 'n' || input === 'N' || key.escape) {
      onReject();
    }
  });

  return (
    <Box
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      height="100%"
    >
      <Box
        flexDirection="column"
        borderStyle="double"
        borderColor="yellow"
        padding={2}
        width={60}
      >
        <Box justifyContent="center" marginBottom={1}>
          <Text bold color="yellow">
            ⚠️  MODE TRANSITION REQUIRED ⚠️
          </Text>
        </Box>

        <Box flexDirection="column" marginY={1}>
          <Text>
            The agent wants to use tool: <Text bold>{toolName}</Text>
          </Text>
          <Text></Text>
          <Text>
            Current Mode: <Text color="green">{currentMode}</Text>
          </Text>
          <Text>
            Required Mode: <Text color="yellow">{requiredMode}</Text>
          </Text>
          <Text></Text>
          <Text>Reason: {reason}</Text>
          <Text></Text>
          <Text>Do you approve switching to {requiredMode} mode?</Text>
        </Box>

        <Box justifyContent="center" marginTop={1}>
          <Box marginX={1}>
            <Text backgroundColor="green" color="black">
              {' '}
              Approve (Y){' '}
            </Text>
          </Box>
          <Box marginX={1}>
            <Text backgroundColor="red" color="black">
              {' '}
              Reject (N){' '}
            </Text>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
