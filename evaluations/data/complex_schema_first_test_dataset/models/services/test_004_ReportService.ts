import { BaseService } from './BaseService.js';

interface ReportResponse {
  reportId: string;
  type: string;
  format: string;
  period: string;
  data: unknown[];
  generatedAt: string;
}

export class ReportService extends BaseService {
  async getReports<T = ReportResponse>(type: string, format: string, period: string): Promise<T> {
    return this.get<T>(`/reports?type=${type}&format=${format}&period=${period}`);
  }
}
