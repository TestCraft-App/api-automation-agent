import { ServiceBase } from "../../base/ServiceBase.js";
import { Response } from "../responses/Response.js";

export class UserService extends ServiceBase {
  constructor() {
    super("/users");
  }

  async getUserById<T>(
    userId: number | string,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    return await this.get<T>(`${this.url}/${userId}`, config);
  }
}
