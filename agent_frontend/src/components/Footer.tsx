import React, { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { format } from 'date-fns';
import type { ModeState } from '../types.js';

interface FooterProps {
  mode: ModeState;
}

export function Footer({ mode }: FooterProps) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  return (
    <Box
      borderStyle="single"
      borderTop={true}
      paddingX={1}
      justifyContent="space-between"
    >
      <Text dimColor>Esc to cancel • Ctrl+C to exit</Text>
      <Box>
        <Text color={mode.color}>▶▶ {mode.current}</Text>
        <Text dimColor> • {format(time, 'HH:mm:ss')}</Text>
      </Box>
    </Box>
  );
}
