import { InjectionToken } from '@angular/core';

/** Empty string = same origin (use `ng serve` proxy to api-gateway). Override for production builds. */
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  providedIn: 'root',
  factory: () => '',
});
