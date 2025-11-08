export interface UserListResponse {
  data: Array<{
    id: number;
    name: string;
    email: string;
    age?: number;
  }>;
  total: number;
}
