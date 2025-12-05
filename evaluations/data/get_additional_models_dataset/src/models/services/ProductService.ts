import { ServiceBase } from "../../base/ServiceBase.js";
import { Response } from "../responses/Response.js";
import { ProductModel } from "../requests/ProductModel.js";

export class ProductService extends ServiceBase {
  constructor() {
    super("/products");
  }

  async createProduct<T>(
    productData: ProductModel,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    return await this.post<T>(this.url, productData, config);
  }

  async getProductById<T>(
    productId: number,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    return await this.get<T>(`${this.url}/${productId}`, config);
  }
}
