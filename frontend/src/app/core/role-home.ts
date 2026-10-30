import { Role } from './models';

export function roleHome(role: Role | null | undefined): string {
  switch (role) {
    case 'super_admin':
      return '/admin';
    case 'company_admin':
      return '/company';
    default:
      return '/chat';
  }
}
