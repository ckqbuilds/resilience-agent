export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface ModeState {
  current: string;
  color: string;
  description: string;
}

export interface AgentResponse {
  content: string;
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
