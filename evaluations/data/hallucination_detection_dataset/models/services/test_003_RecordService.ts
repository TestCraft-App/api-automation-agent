import { BaseService } from './BaseService.js';

interface RecordItem {
  id: string;
  value: string;
  timestamp: string;
}

interface RecordsResponse {
  records: RecordItem[];
}

export class RecordService extends BaseService {
  async getRecords<T = RecordsResponse>(): Promise<T> {
    return this.get<T>('/records');
  }
}
