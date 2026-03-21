import { OrderItemModel } from './OrderItemModel.js';

export interface ShippingAddress {
  street: string;
  city: string;
  state?: string;
  zipCode: string;
  country: string;
}

export interface OrderModel {
  items: OrderItemModel[];
  customerId: string;
  shippingAddress: ShippingAddress;
}
