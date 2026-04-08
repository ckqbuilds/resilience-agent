import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';
import type { AgentEvent } from '../types.js';

interface ActionLogProps {
  events: AgentEvent[];
}

export function ActionLog({ events }: ActionLogProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Handle keyboard input for toggling
  useInput((input) => {
    if (input === '`') {
      setIsExpanded((prev) => !prev);
    }
  });

  if (!events || events.length === 0) return null;

  // Group events by tool call
  const toolCalls = events.filter((e) => e.type === 'tool_call_start');
  const toolResults = events.filter((e) => e.type === 'tool_call_end');
  const errors = events.filter((e) => e.type === 'tool_call_error');

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box
        borderStyle="round"
        borderColor="blue"
        paddingX={1}
        paddingY={0}
        flexDirection="column"
      >
        {/* Header - always visible */}
        <Box justifyContent="space-between">
          <Text color="blue">
            {isExpanded ? '▼' : '▶'} Agent Actions ({toolCalls.length} tool{' '}
            {toolCalls.length === 1 ? 'call' : 'calls'}
            {errors.length > 0 && `, ${errors.length} error${errors.length === 1 ? '' : 's'}`})
          </Text>
          <Text dimColor>Press '`' to toggle</Text>
        </Box>

        {/* Expanded view */}
        {isExpanded && (
          <Box flexDirection="column" marginTop={1}>
            {toolCalls.map((call, idx) => {
              const result = toolResults.find((r) => r.tool_name === call.tool_name);
              const error = errors.find((e) => e.tool_name === call.tool_name);
              const isSubAgent = ['aws_knowledge_agent', 'discovery_agent'].includes(
                call.tool_name || ''
              );

              return (
                <Box key={idx} flexDirection="column" marginY={0}>
                  {isSubAgent ? (
                    <Text color="cyan">→ Invoking {call.tool_name}</Text>
                  ) : (
                    <Text dimColor>• {call.tool_name}</Text>
                  )}

                  {error && (
                    <Box marginLeft={2}>
                      <Text color="red">  ✗ Error: {error.error}</Text>
                    </Box>
                  )}

                  {result && !error && (
                    <Box marginLeft={2}>
                      <Text dimColor>  ✓ {result.result}</Text>
                    </Box>
                  )}
                </Box>
              );
            })}
          </Box>
        )}
      </Box>
    </Box>
  );
}
