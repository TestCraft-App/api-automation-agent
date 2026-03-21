import { BaseService } from './BaseService.js';

interface NoteModel {
  title: string;
  content: string;
}

interface NoteResponse {
  id: string;
  title: string;
  content: string;
  createdAt: string;
}

export class NoteService extends BaseService {
  async createNote<T = NoteResponse>(note: NoteModel): Promise<T> {
    return this.post<T>('/notes', note);
  }
}
