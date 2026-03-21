import { BaseService } from './BaseService.js';

interface NotificationResponse {
  id: string;
  type: string;
  status: string;
  sentAt: string;
}

export class NotificationService extends BaseService {
  async sendNotification<T = NotificationResponse>(notification: Record<string, unknown>): Promise<T> {
    return this.post<T>('/notifications', notification);
  }
}
