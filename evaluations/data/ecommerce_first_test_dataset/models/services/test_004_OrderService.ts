import { BaseService } from './BaseService.js';
import { OrderModel } from '../requests/OrderModel.js';

interface OrderResponse {
  id: string;
  items: Array<{ productId: string; quantity: number; unitPrice: number }>;
  customerId: string;
  shippingAddress: {
    street: string;
    city: string;
    state?: string;
    zipCode: string;
    country: string;
  };
  status: string;
  totalAmount: number;
  createdAt: string;
}

export class OrderService extends BaseService {
  async createOrder<T = OrderResponse>(order: OrderModel): Promise<T> {
    return this.post<T>('/orders', order);
  }

  async getOrderById<T = OrderResponse>(orderId: string): Promise<T> {
    return this.get<T>(`/orders/${orderId}`);
  }
}
