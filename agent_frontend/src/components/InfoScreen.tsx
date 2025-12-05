import React, { useState, useEffect } from 'react';
import { Box, Text, useInput } from 'ink';
import Spinner from 'ink-spinner';
import type { ModeState, AWSConfig, ModelConfig, SessionStats } from '../types.js';
import { AgentService } from '../services/AgentService.js';

interface InfoScreenProps {
  modeState: ModeState;
  onClose: () => void;
}

export function InfoScreen({ modeState, onClose }: InfoScreenProps) {
  const [loading, setLoading] = useState(true);
  const [awsConfig, setAwsConfig] = useState<AWSConfig | null>(null);
  const [modelConfig, setModelConfig] = useState<ModelConfig | null>(null);
  const [sessionStats, setSessionStats] = useState<SessionStats | null>(null);

  useInput((input, key) => {
    if (input === 'i' || input === 'I' || key.escape) {
      onClose();
    }
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const agentService = new AgentService();
        const info = await agentService.getInfo();
        setAwsConfig(info.aws);
        setModelConfig(info.model);
        setSessionStats(info.stats);
      } catch (error) {
        console.error('Failed to fetch info:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <Box
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        height="100%"
      >
        <Box>
          <Spinner type="dots" />
          <Text> Loading information...</Text>
        </Box>
      </Box>
    );
  }

  const contextPercentage = sessionStats
    ? ((sessionStats.tokensUsed / sessionStats.tokensTotal) * 100).toFixed(1)
    : '0';

  return (
    <Box
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      height="100%"
    >
      <Box
        flexDirection="column"
        borderStyle="round"
        borderColor="cyan"
        padding={2}
        width={80}
      >
        <Box justifyContent="center" marginBottom={1}>
          <Text bold color="cyan">
            LLM Information & Progress
          </Text>
        </Box>

        {/* Operation Mode Section */}
        <Box
          flexDirection="column"
          borderStyle="single"
          borderColor="blue"
          padding={1}
          marginY={1}
        >
          <Text bold color="cyan">
            Operation Mode
          </Text>
          <Box marginTop={1}>
            <Box width={20}>
              <Text color="gray">Current Mode:</Text>
            </Box>
            <Text color={modeState.color}>
              {modeState.current} - {modeState.description}
            </Text>
          </Box>
        </Box>

        {/* Model Information Section */}
        {modelConfig && (
          <Box
            flexDirection="column"
            borderStyle="single"
            borderColor="blue"
            padding={1}
            marginY={1}
          >
            <Text bold color="cyan">
              Model Information
            </Text>
            <Box marginTop={1} flexDirection="column">
              <Box>
                <Box width={20}>
                  <Text color="gray">Model:</Text>
                </Box>
                <Text>{modelConfig.modelId}</Text>
              </Box>
              <Box>
                <Box width={20}>
                  <Text color="gray">Max Tokens:</Text>
                </Box>
                <Text>{modelConfig.maxTokens}</Text>
              </Box>
              <Box>
                <Box width={20}>
                  <Text color="gray">Temperature:</Text>
                </Box>
                <Text>{modelConfig.temperature}</Text>
              </Box>
              <Box>
                <Box width={20}>
                  <Text color="gray">Tools:</Text>
                </Box>
                <Text>{modelConfig.tools.join(', ')}</Text>
              </Box>
            </Box>
          </Box>
        )}

        {/* Context Usage Section */}
        {sessionStats && (
          <Box
            flexDirection="column"
            borderStyle="single"
            borderColor="blue"
            padding={1}
            marginY={1}
          >
            <Text bold color="cyan">
              Context Usage
            </Text>
            <Box marginTop={1}>
              <Text>
                Tokens Used: {sessionStats.tokensUsed} / {sessionStats.tokensTotal}
              </Text>
            </Box>
            <Box marginTop={1}>
              <Text>{contextPercentage}% of context window used</Text>
            </Box>
          </Box>
        )}

        {/* AWS Configuration Section */}
        {awsConfig && (
          <Box
            flexDirection="column"
            borderStyle="single"
            borderColor="blue"
            padding={1}
            marginY={1}
          >
            <Text bold color="cyan">
              AWS Configuration
            </Text>
            <Box marginTop={1} flexDirection="column">
              <Box>
                <Box width={20}>
                  <Text color="gray">Region:</Text>
                </Box>
                <Text>{awsConfig.region}</Text>
              </Box>
              <Box>
                <Box width={20}>
                  <Text color="gray">Profile:</Text>
                </Box>
                <Text>{awsConfig.profile}</Text>
              </Box>
              <Box>
                <Box width={20}>
                  <Text color="gray">Account ID:</Text>
                </Box>
                <Text>{awsConfig.accountId}</Text>
              </Box>
            </Box>
          </Box>
        )}

        {/* Session Statistics Section */}
        {sessionStats && (
          <Box
            flexDirection="column"
            borderStyle="single"
            borderColor="blue"
            padding={1}
            marginY={1}
          >
            <Text bold color="cyan">
              Session Statistics
            </Text>
            <Box marginTop={1} flexDirection="column">
              <Box>
                <Box width={20}>
                  <Text color="gray">Total Requests:</Text>
                </Box>
                <Text>{sessionStats.totalRequests}</Text>
              </Box>
              <Box>
                <Box width={20}>
                  <Text color="gray">Avg Response Time:</Text>
                </Box>
                <Text>{sessionStats.avgResponseTime}</Text>
              </Box>
              <Box>
                <Box width={20}>
                  <Text color="gray">Total Cost:</Text>
                </Box>
                <Text>{sessionStats.totalCost}</Text>
              </Box>
              <Box>
                <Box width={20}>
                  <Text color="gray">Session Duration:</Text>
                </Box>
                <Text>{sessionStats.sessionDuration}</Text>
              </Box>
            </Box>
          </Box>
        )}

        <Box marginTop={1} justifyContent="center">
          <Text color="gray">Press 'i' or 'ESC' to close</Text>
        </Box>
      </Box>
    </Box>
  );
}
