export interface Response<T> {
  data: T;
  status: number;
  headers: Record<string, string | number | boolean | string[]>;
  responseTime: number;
}
