import { BaseService } from './BaseService.js';

interface SearchResult {
  id: string;
  name: string;
  price: number;
  category: string;
}

interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
}

export class ProductService extends BaseService {
  async searchProducts<T = SearchResponse>(query: string, sort?: string): Promise<T> {
    const params = sort ? `?q=${query}&sort=${sort}` : `?q=${query}`;
    return this.get<T>(`/products/search${params}`);
  }
}
