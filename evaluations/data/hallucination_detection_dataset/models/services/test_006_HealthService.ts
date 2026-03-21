import { BaseService } from './BaseService.js';

interface HealthResponse {
  status: string;
  uptime: number;
}

export class HealthService extends BaseService {
  async getHealth<T = HealthResponse>(): Promise<T> {
    return this.get<T>('/health');
  }
}
