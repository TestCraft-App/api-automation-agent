import axios from "axios";

axios.interceptors.request.use(
  function (config) {
    console.log("REQUEST:", config.method, config.url);
    return config;
  },
  function (error) {
    console.log("REQUEST ERROR:", error);
  },
  { synchronous: true, runWhen: () => true }
);

axios.interceptors.response.use(
  function onFulfilled(response) {
    console.log(
      "RESPONSE:",
      response.status,
      response.config.url,
      JSON.stringify(response.data)
    );
    return response;
  },
  function onRejected(error) {
    console.log("RESPONSE ERROR:", JSON.stringify(error));
  }
);