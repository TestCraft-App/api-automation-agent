export interface ProductModel {
  name: string;
  price: number;
  description?: string;
  category: string;
  inStock?: boolean;
  tags?: string[];
}
