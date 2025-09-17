import axios, { AxiosStatic } from "axios";
import util from "util";
import "dotenv/config";

export abstract class ApiClientBase {
  client: AxiosStatic = axios;

  protected constructor() {
    axios.defaults.headers.common = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };

    axios.defaults.validateStatus = () => true;

    if (process.env["HTTP_DEBUG"] === "true") {
      axios.interceptors.request.use(
        function (config) {
          console.log("REQUEST:", config.method, config.url, config.headers);
          if (config.data) {
            console.log(
              "REQUEST BODY:",
              util.inspect(config.data, { depth: null, colors: true })
            );
          }
          return config;
        },
        function (error) {
          console.log("REQUEST ERROR:", error);
          return Promise.reject(error);
        },
        { synchronous: true, runWhen: () => true }
      );

      axios.interceptors.response.use(
        function onFulfilled(response) {
          console.log(
            "RESPONSE:",
            response.status,
            response.config.url
          );
          console.log(
            "RESPONSE DATA:",
            util.inspect(response.data, { depth: null, colors: true })
          );
          return response;
        },
        function onRejected(error) {
          console.log(
            "RESPONSE ERROR:",
            util.inspect(error, { depth: null, colors: true })
          );
          return Promise.reject(error);
        }
      );
    }
  }
}
