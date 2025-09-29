import "dotenv/config";
import { ApiClientBase } from "./ApiClientBase.js";

export class ApiClient extends ApiClientBase {
  private static classInstance?: ApiClient;

  private constructor() {
    super();
  }

  public static getInstance() {
    if (!this.classInstance) {
      this.classInstance = new ApiClient();
    }

    return this.classInstance;
  }
}
