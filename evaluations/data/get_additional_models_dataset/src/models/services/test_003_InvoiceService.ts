import { ServiceBase } from "../../base/ServiceBase.js";
import { Response } from "../responses/Response.js";
import { InvoiceModel } from "../requests/InvoiceModel.js";

export class InvoiceService extends ServiceBase {
  constructor() {
    super("/invoices");
  }

  async createInvoice<T>(
    invoiceData: InvoiceModel,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    return await this.post<T>(this.url, invoiceData, config);
  }

  async getInvoicesByOrderId<T>(
    orderId: number,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    return await this.get<T>(`${this.url}?orderId=${orderId}`, config);
  }

  async getInvoicesByUserId<T>(
    userId: number,
    config = this.defaultConfig
  ): Promise<Response<T>> {
    return await this.get<T>(`${this.url}?userId=${userId}`, config);
  }
}
