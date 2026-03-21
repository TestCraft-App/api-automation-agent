import { BaseService } from './BaseService.js';
import { InvoiceModel } from '../requests/InvoiceModel.js';

interface InvoiceResponse {
  id: string;
  customerId: string;
  lineItems: Array<{
    description: string;
    quantity: number;
    unitPrice: number;
    tax: number;
  }>;
  totalAmount: number;
  createdAt: string;
}

export class InvoiceService extends BaseService {
  async createInvoice<T = InvoiceResponse>(invoice: InvoiceModel): Promise<T> {
    return this.post<T>('/invoices', invoice);
  }
}
