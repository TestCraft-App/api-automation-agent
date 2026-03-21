import { BaseService } from './BaseService.js';

interface ProductItem {
  id: string;
  name: string;
  price: number;
  category: string;
  inStock: boolean;
}

interface ProductsListResponse {
  products: ProductItem[];
  total: number;
  page: number;
  limit: number;
}

export class ProductService extends BaseService {
  async listProducts<T = ProductsListResponse>(params?: Record<string, string | number | boolean>): Promise<T> {
    const queryString = params ? '?' + Object.entries(params).map(([k, v]) => `${k}=${v}`).join('&') : '';
    return this.get<T>(`/products${queryString}`);
  }
}
