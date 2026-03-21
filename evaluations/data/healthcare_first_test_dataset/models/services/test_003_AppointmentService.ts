import { BaseService } from './BaseService.js';
import { AppointmentModel } from '../requests/AppointmentModel.js';

interface AppointmentResponse {
  id: string;
  patientId: string;
  dateTime: string;
  duration: number;
  type: string;
  notes?: string;
  status: string;
}

export class AppointmentService extends BaseService {
  async createAppointment<T = AppointmentResponse>(patientId: string, appointment: AppointmentModel): Promise<T> {
    return this.post<T>(`/patients/${patientId}/appointments`, appointment);
  }
}
