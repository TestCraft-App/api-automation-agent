export interface PaymentModel {
  amount: number;
  currency: 'USD' | 'EUR' | 'GBP';
  method: 'credit_card' | 'debit_card' | 'bank_transfer' | 'wallet';
}
