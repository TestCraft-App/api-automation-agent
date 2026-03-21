import { BaseService } from './BaseService.js';

interface UserResponse {
  id: string;
  name: string;
  email: string;
  age?: number;
}

export class UserService extends BaseService {
  async getUserById<T = UserResponse>(userId: string): Promise<T> {
    return this.get<T>(`/users/${userId}`);
  }
}
