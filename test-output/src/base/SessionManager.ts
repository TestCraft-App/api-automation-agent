export class SessionManager {
  private static authTokenCache: {
    [key: string]: { token: string; timestamp: number } | null;
  } = {};

  private static tokenExpiryDuration = 15 * 60 * 1000; // 15 minutes

  static getCachedToken(username: string, password: string): string | null {
    const cacheKey = `${username}:${password}`;
    const cachedData = SessionManager.authTokenCache[cacheKey];

    if (cachedData) {
      const currentTime = Date.now();
      const tokenAge = currentTime - cachedData.timestamp;

      if (tokenAge < SessionManager.tokenExpiryDuration) {
        return cachedData.token;
      } else {
        delete SessionManager.authTokenCache[cacheKey];
      }
    }

    return null;
  }

  static storeToken(username: string, password: string, token: string): void {
    const cacheKey = `${username}:${password}`;
    SessionManager.authTokenCache[cacheKey] = {
      token,
      timestamp: Date.now(),
    };
  }
}
