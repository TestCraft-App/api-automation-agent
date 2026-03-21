import { BaseService } from './BaseService.js';

interface BookResponse {
  id: string;
  title: string;
  author: string;
}

export class BookService extends BaseService {
  async getBookById<T = BookResponse>(id: string): Promise<T> {
    return this.get<T>(`/books/${id}`);
  }
}
