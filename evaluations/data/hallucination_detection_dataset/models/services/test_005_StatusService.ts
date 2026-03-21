import { BaseService } from './BaseService.js';

interface StatusModel {
  name: string;
  status: 'active' | 'inactive' | 'pending';
}

interface StatusResponse {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'pending';
}

export class StatusService extends BaseService {
  async createStatus<T = StatusResponse>(data: StatusModel): Promise<T> {
    return this.post<T>('/statuses', data);
  }
}
