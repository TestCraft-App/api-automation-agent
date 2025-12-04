import { ServiceBase } from "../../base/ServiceBase.js";
import { Response } from "../responses/Response.js";
import { OrderModel } from "../requests/OrderModel.js";

export class OrderService extends ServiceBase {
  constructor() {
    super("/orders");
  }

  async createOrder<T>(
    orderData: OrderModel,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    return await this.post<T>(this.url, orderData, config);
  }

  async getOrderById<T>(
    orderId: number,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    return await this.get<T>(`${this.url}/${orderId}`, config);
  }
}
