import { ServiceBase } from "../../base/ServiceBase.js";
import { Response } from "../responses/Response.js";
import { UserModel } from "../requests/test_001_UserModel.js";

export class UserService extends ServiceBase {
  constructor() {
    super("/users");
  }

  async createUser<T>(
    userData: UserModel,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    return await this.post<T>(this.url, userData, config);
  }
}
