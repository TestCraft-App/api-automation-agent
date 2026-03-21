export interface LineItem {
  description: string;
  quantity: number;
  unitPrice: number;
  tax?: number;
}

export interface InvoiceModel {
  customerId: string;
  lineItems: LineItem[];
  notes?: string;
}
