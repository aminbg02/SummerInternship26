import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth';
import { LanguageService } from '../../core/language';
import { roleHome } from '../../core/role-home';
import { LanguageSwitcher } from '../../shared/language-switcher/language-switcher';

@Component({
  selector: 'app-login',
  imports: [FormsModule, LanguageSwitcher],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  private auth = inject(AuthService);
  private router = inject(Router);
  readonly lang = inject(LanguageService);

  email = '';
  password = '';
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  submit(): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.error.set(null);
    this.auth.login(this.email.trim().toLowerCase(), this.password).subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigate([roleHome(this.auth.user()?.role)]);
      },
      error: (err: HttpErrorResponse) => {
        this.loading.set(false);
        this.error.set(this.loginError(err));
      },
    });
  }

  private loginError(err: HttpErrorResponse): string {
    if (err.status === 0) return this.lang.t('login.errorNoServer');
    if (err.status === 401) return this.lang.t('login.errorInvalid');
    return this.lang.t('login.errorGeneric', { status: err.status });
  }
}
