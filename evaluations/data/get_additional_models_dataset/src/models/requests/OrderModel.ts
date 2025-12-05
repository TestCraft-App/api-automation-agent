export interface OrderModel {
  id?: number | undefined;
  userId: number;
  productId: number;
  quantity: number;
  totalPrice?: number | undefined;
}
