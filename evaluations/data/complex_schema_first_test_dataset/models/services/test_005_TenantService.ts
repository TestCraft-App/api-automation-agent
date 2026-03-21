import { BaseService } from './BaseService.js';

interface TenantConfigResponse {
  tenantId: string;
  name: string;
  features: string[];
  locale: string;
  apiVersion: string;
}

export class TenantService extends BaseService {
  async getTenantConfig<T = TenantConfigResponse>(
    apiVersion: string,
    tenantId: string,
    language: string
  ): Promise<T> {
    return this.get<T>('/tenants/config', {
      headers: {
        'X-API-Version': apiVersion,
        'X-Tenant-ID': tenantId,
        'Accept-Language': language
      }
    });
  }
}
