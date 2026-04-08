import axios from 'axios';
import type {
  AgentResponse,
  AWSConfig,
  ModelConfig,
  SessionStats,
  ProfileInfo,
  ProfileSwitchResponse,
  ProvidersResponse,
  ModelSwitchRequest,
  ModelSwitchResponse
} from '../types.js';

export class AgentService {
  private baseUrl: string;
  private sessionId: string;

  constructor() {
    this.baseUrl = process.env.API_URL || 'http://localhost:8001';
    this.sessionId = Math.random().toString(36).substring(7);
  }

  async sendMessage(message: string): Promise<AgentResponse> {
    try {
      const response = await axios.post(`${this.baseUrl}/api/chat`, {
        message,
        sessionId: this.sessionId,
      });

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.detail || error.message || 'Failed to send message'
        );
      }
      throw error;
    }
  }

  async respondToInterrupt(
    interruptId: string,
    approved: boolean
  ): Promise<AgentResponse> {
    try {
      const response = await axios.post(`${this.baseUrl}/api/interrupt`, {
        interruptId,
        approved,
        sessionId: this.sessionId,
      });

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.detail || error.message || 'Failed to respond to interrupt'
        );
      }
      throw error;
    }
  }

  async getInfo(): Promise<{
    aws: AWSConfig;
    model: ModelConfig;
    stats: SessionStats;
  }> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/info`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.detail || error.message || 'Failed to fetch info'
        );
      }
      throw error;
    }
  }

  async listProfiles(): Promise<ProfileInfo> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/profiles`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.detail || error.message || 'Failed to fetch profiles'
        );
      }
      throw error;
    }
  }

  async switchProfile(profile: string): Promise<ProfileSwitchResponse> {
    try {
      const response = await axios.post(`${this.baseUrl}/api/profiles/switch`, {
        profile,
      });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.detail || error.message || 'Failed to switch profile'
        );
      }
      throw error;
    }
  }

  async listModelProviders(): Promise<ProvidersResponse> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/models/providers`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.detail || error.message || 'Failed to fetch model providers'
        );
      }
      throw error;
    }
  }

  async switchModel(request: ModelSwitchRequest): Promise<ModelSwitchResponse> {
    try {
      const response = await axios.post(`${this.baseUrl}/api/models/switch`, request);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.detail || error.message || 'Failed to switch model'
        );
      }
      throw error;
    }
  }
}
