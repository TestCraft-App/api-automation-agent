import { ServiceBase } from "../../base/ServiceBase.js";
import { Response } from "../responses/Response.js";
import { CategoryModel } from "../requests/CategoryModel.js";

export class CategoryService extends ServiceBase {
  constructor() {
    super("/categories");
  }

  async createCategory<T>(
    categoryData: CategoryModel,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    return await this.post<T>(this.url, categoryData, config);
  }

  async getAllCategories<T>(config = this.defaultConfig): Promise<Response<T>> {
    return await this.get<T>(this.url, config);
  }
}
