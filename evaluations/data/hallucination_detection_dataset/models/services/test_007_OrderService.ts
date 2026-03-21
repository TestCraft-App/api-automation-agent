import { BaseService } from './BaseService.js';

interface OrderModel {
  productName: string;
  quantity: number;
}

interface OrderResponse {
  id: string;
  productName: string;
  quantity: number;
  createdAt: string;
  updatedAt: string;
}

export class OrderService extends BaseService {
  async createOrder<T = OrderResponse>(order: OrderModel): Promise<T> {
    return this.post<T>('/orders', order);
  }
}
