import { BaseService } from './BaseService.js';

interface ProductItem {
  id: string;
  name: string;
  price: number;
}

interface ProductsResponse {
  products: ProductItem[];
}

export class ProductService extends BaseService {
  async listProducts<T = ProductsResponse>(category?: string): Promise<T> {
    const params = category ? `?category=${category}` : '';
    return this.get<T>(`/products${params}`);
  }
}
