import { ServiceBase } from "../../base/ServiceBase.js";
import { Response } from "../responses/Response.js";

export interface Product {
  id: number;
  name: string;
  price: number;
}

export interface ProductsResponse {
  products: Product[];
  pagination: {
    page: number;
    total: number;
  };
}

export class ProductService extends ServiceBase {
  constructor() {
    super("/products");
  }

  async listProducts<T>(
    page: number = 1,
    limit: number = 10,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });
    return await this.get<T>(`${this.url}?${params.toString()}`, config);
  }
}
