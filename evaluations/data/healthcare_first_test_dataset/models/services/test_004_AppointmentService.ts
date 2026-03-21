import { BaseService } from './BaseService.js';

interface AppointmentItem {
  id: string;
  patientId: string;
  dateTime: string;
  duration: number;
  type: string;
  status: string;
}

interface AppointmentsResponse {
  appointments: AppointmentItem[];
  total: number;
}

export class AppointmentService extends BaseService {
  async listAppointments<T = AppointmentsResponse>(patientId: string, from?: string, to?: string): Promise<T> {
    const params: string[] = [];
    if (from) params.push(`from=${from}`);
    if (to) params.push(`to=${to}`);
    const queryString = params.length > 0 ? `?${params.join('&')}` : '';
    return this.get<T>(`/patients/${patientId}/appointments${queryString}`);
  }
}
