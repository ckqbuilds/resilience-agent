import React, { useState, useEffect } from 'react';
import { Box, Text, useInput } from 'ink';
import Spinner from 'ink-spinner';
import type { ModeState, AWSConfig, ModelConfig, SessionStats, ProfileInfo, ProvidersResponse } from '../types.js';
import { AgentService } from '../services/AgentService.js';

interface InfoScreenProps {
  modeState: ModeState;
  onClose: () => void;
}

type FocusSection = 'profile' | 'model';

export function InfoScreen({ modeState, onClose }: InfoScreenProps) {
  const [loading, setLoading] = useState(true);
  const [awsConfig, setAwsConfig] = useState<AWSConfig | null>(null);
  const [modelConfig, setModelConfig] = useState<ModelConfig | null>(null);
  const [sessionStats, setSessionStats] = useState<SessionStats | null>(null);
  const [profileInfo, setProfileInfo] = useState<ProfileInfo | null>(null);
  const [selectedProfileIndex, setSelectedProfileIndex] = useState(0);
  const [switching, setSwitching] = useState(false);

  // Model provider state
  const [providersInfo, setProvidersInfo] = useState<ProvidersResponse | null>(null);
  const [selectedProviderIndex, setSelectedProviderIndex] = useState(0);
  const [selectedModelIndex, setSelectedModelIndex] = useState(0);
  const [switchingModel, setSwitchingModel] = useState(false);
  const [focusSection, setFocusSection] = useState<FocusSection>('profile');

  useInput((input, key) => {
    if (switching || switchingModel) return; // Disable input while switching

    if (input === 'i' || input === 'I' || key.escape) {
      onClose();
    }

    // Tab to switch between sections
    if (key.tab) {
      setFocusSection((prev) => (prev === 'profile' ? 'model' : 'profile'));
      return;
    }

    // Profile section navigation
    if (focusSection === 'profile' && profileInfo && profileInfo.profiles.length > 0) {
      if (key.upArrow) {
        setSelectedProfileIndex((prev) =>
          prev > 0 ? prev - 1 : profileInfo.profiles.length - 1
        );
      } else if (key.downArrow) {
        setSelectedProfileIndex((prev) =>
          prev < profileInfo.profiles.length - 1 ? prev + 1 : 0
        );
      } else if (key.return) {
        const selectedProfile = profileInfo.profiles[selectedProfileIndex];
        if (selectedProfile && selectedProfile !== profileInfo.current) {
          handleProfileSwitch(selectedProfile);
        }
      }
    }

    // Model section navigation
    if (focusSection === 'model' && providersInfo) {
      const providerNames = Object.keys(providersInfo.providers);
      const currentProvider = providerNames[selectedProviderIndex];
      if (!currentProvider) return;
      const models = providersInfo.providers[currentProvider]?.models || [];

      if (key.leftArrow) {
        // Navigate providers
        setSelectedProviderIndex((prev) =>
          prev > 0 ? prev - 1 : providerNames.length - 1
        );
        setSelectedModelIndex(0); // Reset model selection when changing provider
      } else if (key.rightArrow) {
        // Navigate providers
        setSelectedProviderIndex((prev) =>
          prev < providerNames.length - 1 ? prev + 1 : 0
        );
        setSelectedModelIndex(0); // Reset model selection when changing provider
      } else if (key.upArrow) {
        // Navigate models
        setSelectedModelIndex((prev) =>
          prev > 0 ? prev - 1 : models.length - 1
        );
      } else if (key.downArrow) {
        // Navigate models
        setSelectedModelIndex((prev) =>
          prev < models.length - 1 ? prev + 1 : 0
        );
      } else if (key.return) {
        // Switch to selected model
        const selectedModel = models[selectedModelIndex];
        if (selectedModel && (currentProvider !== providersInfo.current.provider || selectedModel.id !== providersInfo.current.model_id)) {
          handleModelSwitch(currentProvider, selectedModel.id);
        }
      }
    }
  });

  const handleProfileSwitch = async (profile: string) => {
    setSwitching(true);
    try {
      const agentService = new AgentService();
      const result = await agentService.switchProfile(profile);

      // Update AWS config with new profile info
      setAwsConfig({
        region: result.region,
        profile: result.profile,
        accountId: result.accountId,
      });

      // Update profile info to reflect current profile
      if (profileInfo) {
        setProfileInfo({
          ...profileInfo,
          current: result.profile,
        });
      }
    } catch (error) {
      console.error('Failed to switch profile:', error);
    } finally {
      setSwitching(false);
    }
  };

  const handleModelSwitch = async (provider: string, modelId: string) => {
    setSwitchingModel(true);
    try {
      const agentService = new AgentService();
      const result = await agentService.switchModel({
        provider,
        model_id: modelId,
      });

      // Update model config with new model info
      setModelConfig({
        provider: result.provider,
        modelId: result.modelId,
        maxTokens: result.maxTokens,
        temperature: result.temperature,
        tools: modelConfig?.tools || [],
      });

      // Update providers info to reflect current model
      if (providersInfo) {
        setProvidersInfo({
          ...providersInfo,
          current: {
            provider: result.provider,
            model_id: result.model_id,
          },
        });
      }
    } catch (error) {
      console.error('Failed to switch model:', error);
    } finally {
      setSwitchingModel(false);
    }
  };

  useEffect(() => {
    const abortController = new AbortController();
    let isMounted = true;

    const fetchData = async () => {
      try {
        const agentService = new AgentService();
        const [info, profiles, providers] = await Promise.all([
          agentService.getInfo(),
          agentService.listProfiles(),
          agentService.listModelProviders(),
        ]);

        if (isMounted && !abortController.signal.aborted) {
          setAwsConfig(info.aws);
          setModelConfig(info.model);
          setSessionStats(info.stats);
          setProfileInfo(profiles);
          setProvidersInfo(providers);

          // Set initial selected index to current profile
          const currentIndex = profiles.profiles.indexOf(profiles.current);
          setSelectedProfileIndex(currentIndex >= 0 ? currentIndex : 0);

          // Set initial selected index to current provider
          const providerNames = Object.keys(providers.providers);
          const currentProviderIndex = providerNames.indexOf(providers.current.provider);
          setSelectedProviderIndex(currentProviderIndex >= 0 ? currentProviderIndex : 0);

          // Set initial selected index to current model
          const currentProvider = providers.providers[providers.current.provider];
          if (currentProvider) {
            const currentModelIndex = currentProvider.models.findIndex(
              (m) => m.id === providers.current.model_id
            );
            setSelectedModelIndex(currentModelIndex >= 0 ? currentModelIndex : 0);
          }
        }
      } catch (error) {
        if (isMounted && !abortController.signal.aborted) {
          console.error('Failed to fetch info:', error);
        }
      } finally {
        if (isMounted && !abortController.signal.aborted) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      isMounted = false;
      abortController.abort();
    };
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
                  <Text color="gray">Provider:</Text>
                </Box>
                <Text>{modelConfig.provider || 'anthropic'}</Text>
              </Box>
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

        {/* Model Provider & Selection Section */}
        {providersInfo && (
          <Box
            flexDirection="column"
            borderStyle="single"
            borderColor={focusSection === 'model' ? 'green' : 'blue'}
            padding={1}
            marginY={1}
          >
            <Text bold color="cyan">
              Model Provider & Selection {switchingModel && '(Switching...)'}
            </Text>

            {/* Provider tabs */}
            <Box marginTop={1} marginBottom={1}>
              <Text color="gray">Provider: </Text>
              {Object.keys(providersInfo.providers).map((providerName, index) => {
                const isCurrentProvider = providerName === providersInfo.current.provider;
                const isSelectedProvider = index === selectedProviderIndex && focusSection === 'model';

                return (
                  <Text
                    key={providerName}
                    color={
                      switchingModel
                        ? 'gray'
                        : isCurrentProvider
                        ? 'green'
                        : isSelectedProvider
                        ? 'cyan'
                        : 'white'
                    }
                    bold={isCurrentProvider || isSelectedProvider}
                  >
                    {index > 0 ? ' | ' : ''}
                    {isSelectedProvider ? `[${providerName}]` : providerName}
                  </Text>
                );
              })}
            </Box>

            {/* Available models for selected provider */}
            <Box marginTop={1} flexDirection="column">
              <Text color="gray">Available Models:</Text>
              {(() => {
                const providerNames = Object.keys(providersInfo.providers);
                const currentProvider = providerNames[selectedProviderIndex];
                if (!currentProvider) return null;
                const models = providersInfo.providers[currentProvider]?.models || [];

                return models.map((model, index) => {
                  const isCurrent =
                    currentProvider === providersInfo.current.provider &&
                    model.id === providersInfo.current.model_id;
                  const isSelected = index === selectedModelIndex && focusSection === 'model';

                  return (
                    <Box key={model.id}>
                      <Text
                        color={
                          switchingModel
                            ? 'gray'
                            : isCurrent
                            ? 'green'
                            : isSelected
                            ? 'cyan'
                            : 'white'
                        }
                        bold={isCurrent || isSelected}
                      >
                        {isSelected ? '▶ ' : '  '}
                        {model.name}
                        {isCurrent ? ' (current)' : ''}
                      </Text>
                    </Box>
                  );
                });
              })()}
            </Box>

            <Box marginTop={1}>
              <Text color="gray" dimColor>
                Press Tab to switch sections | ←/→ to change provider | ↑/↓ to select model | Enter to switch
              </Text>
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

        {/* AWS Profile Selection Section */}
        {profileInfo && profileInfo.profiles.length > 0 && (
          <Box
            flexDirection="column"
            borderStyle="single"
            borderColor={focusSection === 'profile' ? 'green' : 'blue'}
            padding={1}
            marginY={1}
          >
            <Text bold color="cyan">
              Available AWS Profiles {switching && '(Switching...)'}
            </Text>
            <Box marginTop={1} flexDirection="column">
              {profileInfo.profiles.map((profile, index) => {
                const isCurrent = profile === profileInfo.current;
                const isSelected = index === selectedProfileIndex;

                return (
                  <Box key={profile}>
                    <Text
                      color={
                        switching
                          ? 'gray'
                          : isCurrent
                          ? 'green'
                          : isSelected
                          ? 'cyan'
                          : 'white'
                      }
                      bold={isCurrent || isSelected}
                    >
                      {isSelected ? '▶ ' : '  '}
                      {profile}
                      {isCurrent ? ' (current)' : ''}
                    </Text>
                  </Box>
                );
              })}
            </Box>
            <Box marginTop={1}>
              <Text color="gray" dimColor>
                Press Tab to switch sections | ↑/↓ to select profile | Enter to switch
              </Text>
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
