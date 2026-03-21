import { BaseService } from './BaseService.js';

interface LoginRequest {
  username: string;
  password: string;
}

interface LoginResponse {
  token: string;
  expiresIn: number;
}

export class AuthService extends BaseService {
  async login<T = LoginResponse>(credentials: LoginRequest): Promise<T> {
    return this.post<T>('/auth/login', credentials);
  }
}
