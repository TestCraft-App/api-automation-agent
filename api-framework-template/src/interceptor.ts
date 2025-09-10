import { BatchInterceptor } from "@mswjs/interceptors";
import { ClientRequestInterceptor } from "@mswjs/interceptors/ClientRequest";
import { gunzipSync } from "node:zlib";
import { Buffer } from "buffer";

const interceptor = new BatchInterceptor({
  name: "http-logger",
  interceptors: [new ClientRequestInterceptor()],
});

interceptor.apply();

interceptor.on("request", ({ request }) => {
  console.log("REQUEST:", request.method, request.url);
});

interceptor.on("response", async ({ response, request }) => {
  const buf = Buffer.from(await response.arrayBuffer());

  let body: unknown;
  try {
    const text = gunzipSync(buf).toString("utf8");
    body = JSON.parse(text);
  } catch {
    body = buf.toString("utf8");
  }

  console.log("RESPONSE:", response.status, request.url, body);
});
