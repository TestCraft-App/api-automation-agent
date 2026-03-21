import { BaseService } from './BaseService.js';

interface EmployeeModel {
  firstName: string;
  lastName: string;
  email: string;
  department: string;
  position: string;
  startDate?: string;
  salary?: number;
}

interface EmployeeResponse {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  department: string;
  position: string;
  startDate?: string;
  salary?: number;
}

export class EmployeeService extends BaseService {
  async createEmployee<T = EmployeeResponse>(employee: EmployeeModel): Promise<T> {
    return this.post<T>('/employees', employee);
  }
}
