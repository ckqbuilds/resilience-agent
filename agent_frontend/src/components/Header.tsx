import React from 'react';
import { Box, Text } from 'ink';
import { format } from 'date-fns';
import type { ModeState } from '../types.js';

interface HeaderProps {
  mode: ModeState;
}

export function Header({ mode }: HeaderProps) {
  const [time, setTime] = React.useState(new Date());

  React.useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  return (
    <Box
      borderStyle="single"
      borderBottom={true}
      paddingX={1}
      justifyContent="space-between"
    >
      <Text bold color="cyan">
        Resilience Architect
      </Text>
      <Text color={mode.color}>Mode: {mode.current}</Text>
      <Text color="gray">{format(time, 'HH:mm:ss')}</Text>
    </Box>
  );
}
