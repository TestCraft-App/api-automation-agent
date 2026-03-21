import { BaseService } from './BaseService.js';
import { ItemModel } from '../requests/ItemModel.js';

interface ItemResponse {
  id: string;
  name: string;
  description: string;
  price: number;
}

export class ItemService extends BaseService {
  async createItem<T = ItemResponse>(item: ItemModel): Promise<T> {
    return this.post<T>('/items', item);
  }
}
