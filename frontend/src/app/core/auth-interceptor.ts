import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthService } from './auth';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const token = auth.token;
  if (token) {
    req = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
  }

  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      const isLoginRequest = req.url.includes('/auth/login');

      if (!isLoginRequest && (err.status === 401 || err.status === 422)) {
        auth.logout();
        router.navigate(['/login'], {
          queryParams: { expired: '1' },
        });
      }
      return throwError(() => err);
    }),
  );
};
