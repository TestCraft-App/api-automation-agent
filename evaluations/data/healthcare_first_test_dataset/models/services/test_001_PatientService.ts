import { BaseService } from './BaseService.js';
import { PatientModel } from '../requests/PatientModel.js';

interface PatientResponse {
  id: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  gender: string;
  allergies: string[];
  emergencyContact: {
    name: string;
    phone: string;
    relationship?: string;
  };
}

export class PatientService extends BaseService {
  async createPatient<T = PatientResponse>(patient: PatientModel): Promise<T> {
    return this.post<T>('/patients', patient);
  }
}
