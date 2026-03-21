import { BaseService } from './BaseService.js';
import { UserModel } from '../requests/UserModel.js';

interface UserResponse {
  id: string;
  name: string;
  email: string;
  age?: number;
}

export class UserService extends BaseService {
  async createUser<T = UserResponse>(user: UserModel): Promise<T> {
    return this.post<T>('/users', user);
  }

  async deleteUser(userId: string): Promise<void> {
    return this.delete(`/users/${userId}`);
  }
}
