import { BaseService } from './BaseService.js';
import { PaymentModel } from '../requests/PaymentModel.js';

interface PaymentResponse {
  id: string;
  orderId: string;
  amount: number;
  currency: string;
  method: string;
  status: string;
  createdAt: string;
}

export class PaymentService extends BaseService {
  async createPayment<T = PaymentResponse>(orderId: string, payment: PaymentModel): Promise<T> {
    return this.post<T>(`/orders/${orderId}/payments`, payment);
  }
}
