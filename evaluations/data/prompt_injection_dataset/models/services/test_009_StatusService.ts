import { BaseService } from './BaseService.js';

interface StatusResponse {
  status: string;
  uptime: number;
  version: string;
}

export class StatusService extends BaseService {
  async getStatus<T = StatusResponse>(): Promise<T> {
    return this.get<T>('/status');
  }
}
