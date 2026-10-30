import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth';

import { roleHome } from './role-home';

export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }
  const role = auth.user()?.role;
  if (role !== 'super_admin') {
    router.navigate([roleHome(role)]);
    return false;
  }
  return true;
};
