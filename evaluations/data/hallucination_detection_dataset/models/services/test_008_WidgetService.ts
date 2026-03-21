import { BaseService } from './BaseService.js';

interface WidgetModel {
  name: string;
  type: string;
}

interface WidgetResponse {
  id: string;
  name: string;
  type: string;
}

export class WidgetService extends BaseService {
  async createWidget<T = WidgetResponse>(widget: WidgetModel): Promise<T> {
    return this.post<T>('/widgets', widget);
  }
}
