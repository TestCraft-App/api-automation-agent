export interface InvoiceModel {
  id?: number | undefined;
  orderId: number;
  userId: number;
  amount: number;
  status?: string | undefined;
  createdAt?: string | undefined;
}
