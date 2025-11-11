import { ServiceBase } from "../../base/ServiceBase.js";
import { Response } from "../responses/Response.js";

export interface Order {
  id: string;
  status: string;
  total: number;
}

export interface OrdersResponse {
  orders: Order[];
  count: number;
}

export class OrderService extends ServiceBase {
  constructor() {
    super("/orders");
  }

  async listOrders<T>(
    status?: string,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    const params = status ? `?status=${status}` : "";
    return await this.get<T>(`${this.url}${params}`, config);
  }
}
