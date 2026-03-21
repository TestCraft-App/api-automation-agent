import { BaseService } from './BaseService.js';
import { ProductModel } from '../requests/ProductModel.js';

interface ProductResponse {
  id: string;
  name: string;
  price: number;
  description?: string;
  category: string;
  inStock: boolean;
  tags: string[];
}

export class ProductService extends BaseService {
  async createProduct<T = ProductResponse>(product: ProductModel): Promise<T> {
    return this.post<T>('/products', product);
  }
}
