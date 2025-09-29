import { AxiosResponse, type AxiosRequestConfig } from "axios";
import { ApiClient } from "./ApiClient.js";
import { Response } from "../models/responses/Response.js";
import { SessionManager } from "./SessionManager.js";

export class ServiceBase {
  private api: ApiClient;
  protected url: string;
  protected defaultConfig: AxiosRequestConfig;

  constructor(endpointPath: string) {
    this.api = ApiClient.getInstance();
    this.url = this.baseUrl + endpointPath;
    this.defaultConfig = {};
  }

  get baseUrl(): string {
    return process.env["BASEURL"] ?? "";
  }

  async authenticate(): Promise<void> {
    const username = process.env["USER"];
    const password = process.env["PASSWORD"];

    if (!username || !password) {
      throw new Error("Missing username or password in environment variables.");
    }

    const cachedToken = SessionManager.getCachedToken(username, password);

    if (cachedToken) {
      this.defaultConfig = {
        headers: { Authorization: "Bearer " + cachedToken },
      };
      return;
    }

    // AUTHENTICATION EXAMPLE 
    //
    // const credentials = {
    //   username,
    //   password,
    // };
    // const response = await this.post<SessionResponse>(`${this.baseUrl}/auth`, credentials);

    // SessionManager.storeToken(username, password, response.data.token);

    // this.defaultConfig = {
    //   headers: { Authorization: "Bearer " + response.data.token },
    // };
  }

  protected async get<T>(
    url: string,
    config: AxiosRequestConfig = this.defaultConfig,
  ): Promise<Response<T>> {
    const startTime = Date.now();
    const response = await this.api.client.get<T>(url, config);
    const endTime = Date.now();

    const customResponse: Response<T> = this.buildResponse<T>(endTime, startTime, response);
    return customResponse;
  }

  protected async post<T>(
    url: string,
    data: unknown,
    config: AxiosRequestConfig = this.defaultConfig,
  ): Promise<Response<T>> {
    const startTime = Date.now();
    const response = await this.api.client.post<T>(url, data, config);
    const endTime = Date.now();

    const customResponse: Response<T> = this.buildResponse<T>(endTime, startTime, response);
    return customResponse;
  }

  protected async put<T>(
    url: string,
    data: unknown,
    config: AxiosRequestConfig = this.defaultConfig,
  ): Promise<Response<T>> {
    const startTime = Date.now();
    const response = await this.api.client.put<T>(url, data, config);
    const endTime = Date.now();

    const customResponse: Response<T> = this.buildResponse<T>(endTime, startTime, response);
    return customResponse;
  }

  protected async patch<T>(
    url: string,
    data: unknown,
    config: AxiosRequestConfig = this.defaultConfig,
  ): Promise<Response<T>> {
    const startTime = Date.now();
    const response = await this.api.client.patch<T>(url, data, config);
    const endTime = Date.now();

    const customResponse: Response<T> = this.buildResponse<T>(endTime, startTime, response);
    return customResponse;
  }

  protected async delete<T>(
    url: string,
    config: AxiosRequestConfig = this.defaultConfig,
  ): Promise<Response<T>> {
    const startTime = Date.now();
    const response = await this.api.client.delete<T>(url, config);
    const endTime = Date.now();

    const customResponse: Response<T> = this.buildResponse<T>(endTime, startTime, response);
    return customResponse;
  }

  protected async head<T>(
    url: string,
    config: AxiosRequestConfig = this.defaultConfig,
  ): Promise<Response<T>> {
    const startTime = Date.now();
    const response = await this.api.client.head<T>(url, config);
    const endTime = Date.now();

    const customResponse: Response<T> = this.buildResponse<T>(endTime, startTime, response);
    return customResponse;
  }

  protected async options<T>(
    url: string,
    config: AxiosRequestConfig = this.defaultConfig,
  ): Promise<Response<T>> {
    const startTime = Date.now();
    const response = await this.api.client.options<T>(url, config);
    const endTime = Date.now();

    const customResponse: Response<T> = this.buildResponse<T>(endTime, startTime, response);
    return customResponse;
  }

  private buildResponse<T>(endTime: number, startTime: number, response: AxiosResponse<T>) {
    const responseTime = endTime - startTime;

    const customResponse: Response<T> = {
      data: response.data,
      status: response.status,
      headers: response.headers as Record<string, string | number | boolean | string[]>,
      responseTime: responseTime,
    };
    return customResponse;
  }
}
