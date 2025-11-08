import { ServiceBase } from "../../base/ServiceBase.js";
import { Response } from "../responses/Response.js";
import { UserModel } from "../requests/UserModel.js";
import { UpdateUserModel } from "../requests/UpdateUserModel.js";

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

  async updateUser<T>(
    userId: number | string,
    userData: UpdateUserModel,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    return await this.put<T>(`${this.url}/${userId}`, userData, config);
  }

  async deleteUser<T>(
    userId: number | string,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    return await this.delete<T>(`${this.url}/${userId}`, config);
  }
}
