import { BaseService } from './BaseService.js';

interface ItemModel {
  name: string;
}

interface ItemResponse {
  id: string;
  name: string;
}

export class ItemService extends BaseService {
  async createItem<T = ItemResponse>(item: ItemModel): Promise<T> {
    return this.post<T>('/items', item);
  }
}
