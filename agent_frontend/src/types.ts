export interface AgentEvent {
  type: 'tool_call_start' | 'tool_call_end' | 'tool_call_error' | 'text_chunk';
  tool_name?: string;
  tool_input?: Record<string, any>;
  result?: string;
  error?: string;
  content?: string;
  timestamp: string;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  events?: AgentEvent[];
}

export interface ModeState {
  current: string;
  color: string;
  description: string;
}

export interface AgentResponse {
  content: string;
  events?: AgentEvent[];
  interrupt?: {
    id: string;
    currentMode: string;
    requiredMode: string;
    toolName: string;
    reason: string;
    color?: string;
    description?: string;
  };
}

export interface AWSConfig {
  region: string;
  profile: string;
  accountId: string;
}

export interface ModelConfig {
  provider?: string;
  modelId: string;
  maxTokens: number;
  temperature: number;
  tools: string[];
}

export interface SessionStats {
  totalRequests: number;
  avgResponseTime: string;
  totalCost: string;
  sessionDuration: string;
  tokensUsed: number;
  tokensTotal: number;
}

export interface ProfileInfo {
  profiles: string[];
  current: string;
}

export interface ProfileSwitchResponse {
  success: boolean;
  profile: string;
  region: string;
  accountId: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  max_tokens: number;
}

export interface ModelProvider {
  models: ModelInfo[];
  default_model: string;
  env_var?: string;
  requires_aws?: boolean;
}

export interface ProvidersResponse {
  providers: Record<string, ModelProvider>;
  current: {
    provider: string;
    model_id: string;
  };
}

export interface ModelSwitchRequest {
  provider: string;
  model_id: string;
  config?: Record<string, any>;
}

export interface ModelSwitchResponse {
  success: boolean;
  provider: string;
  model_id: string;
  modelId: string;
  maxTokens: number;
  temperature: number;
}
