import { BaseService } from './BaseService.js';

interface TaskModel {
  title: string;
  status: string;
  priority?: number;
}

interface TaskResponse {
  id: string;
  title: string;
  status: string;
  priority: number;
}

export class TaskService extends BaseService {
  async createTask<T = TaskResponse>(task: TaskModel): Promise<T> {
    return this.post<T>('/tasks', task);
  }
}
