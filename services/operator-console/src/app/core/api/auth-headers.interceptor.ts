import { HttpInterceptorFn } from '@angular/common/http';
import { DEV_AUTH_HEADERS } from './dev-auth-headers';

export const authHeadersInterceptor: HttpInterceptorFn = (req, next) => {
  const withAuth = req.clone({
    setHeaders: DEV_AUTH_HEADERS,
  });
  return next(withAuth);
};
