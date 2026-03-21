import { BaseService } from './BaseService.js';

interface EventItem {
  id: string;
  name: string;
  date: string;
}

interface EventsResponse {
  events: EventItem[];
}

export class EventService extends BaseService {
  async listEvents<T = EventsResponse>(limit?: number): Promise<T> {
    const params = limit ? `?limit=${limit}` : '';
    return this.get<T>(`/events${params}`);
  }
}
