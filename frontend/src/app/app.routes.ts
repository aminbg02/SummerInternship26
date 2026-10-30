import { Routes } from '@angular/router';

import { adminGuard } from './core/admin-guard';
import { authGuard } from './core/auth-guard';
import { companyAdminGuard } from './core/company-admin-guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./auth/login/login').then((m) => m.Login),
  },
  {
    path: 'chat',
    canActivate: [authGuard],
    loadComponent: () => import('./customer/chat/chat').then((m) => m.Chat),
  },
  {
    path: 'requests',
    canActivate: [authGuard],
    loadComponent: () => import('./requests/requests-page').then((m) => m.RequestsPage),
  },
  {
    path: 'company',
    canActivate: [companyAdminGuard],
    loadComponent: () => import('./company/company').then((m) => m.Company),
    children: [
      {
        path: 'kb',
        loadComponent: () => import('./company/kb/kb').then((m) => m.CompanyKb),
      },
      {
        path: 'users',
        loadComponent: () => import('./shared/users/users').then((m) => m.UsersManage),
      },
      {
        path: 'token-requests',
        loadComponent: () =>
          import('./shared/token-requests/token-requests').then((m) => m.TokenRequestsPanel),
      },
      { path: '', pathMatch: 'full', redirectTo: 'kb' },
    ],
  },
  {
    path: 'admin',
    canActivate: [adminGuard],
    loadComponent: () => import('./admin/admin').then((m) => m.Admin),
    children: [
      {
        path: 'providers',
        loadComponent: () =>
          import('./admin/providers/providers').then((m) => m.ProvidersAdmin),
      },
      {
        path: 'pii-rules',
        loadComponent: () =>
          import('./admin/pii-rules/pii-rules').then((m) => m.PiiRulesAdmin),
      },
      {
        path: 'usage',
        loadComponent: () => import('./admin/usage/usage').then((m) => m.UsageAdmin),
      },
      {
        path: 'feedback',
        loadComponent: () =>
          import('./admin/feedback/feedback').then((m) => m.FeedbackAdmin),
      },
      {
        path: 'companies',
        loadComponent: () =>
          import('./admin/companies/companies').then((m) => m.CompaniesAdmin),
      },
      {
        path: 'users',
        loadComponent: () => import('./shared/users/users').then((m) => m.UsersManage),
      },
      {
        path: 'token-requests',
        loadComponent: () =>
          import('./shared/token-requests/token-requests').then((m) => m.TokenRequestsPanel),
      },
      {
        path: 'kb',
        loadComponent: () => import('./admin/kb/kb').then((m) => m.KbAdmin),
      },
      { path: '', pathMatch: 'full', redirectTo: 'providers' },
    ],
  },
  { path: '', pathMatch: 'full', redirectTo: 'chat' },
  { path: '**', redirectTo: 'chat' },
];
