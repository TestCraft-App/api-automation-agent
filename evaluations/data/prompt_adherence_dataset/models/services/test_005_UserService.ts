import { BaseService } from './BaseService.js';
import { PatchUserModel } from '../requests/PatchUserModel.js';

interface UserResponse {
  id: string;
  name: string;
  email: string;
  age?: number;
}

export class UserService extends BaseService {
  async createUser<T = UserResponse>(user: Record<string, unknown>): Promise<T> {
    return this.post<T>('/users', user);
  }

  async patchUser<T = UserResponse>(userId: string, data: PatchUserModel): Promise<T> {
    return this.patch<T>(`/users/${userId}`, data);
  }
}
