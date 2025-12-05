import axios from 'axios';
import type { AgentResponse, AWSConfig, ModelConfig, SessionStats } from '../types.js';

export class AgentService {
  private baseUrl: string;
  private sessionId: string;

  constructor() {
    this.baseUrl = process.env.API_URL || 'http://localhost:8000';
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
}
