import { Component, computed, inject } from '@angular/core';
import { RouterLink, Router } from '@angular/router';

import { AuthService } from '../core/auth';
import { LanguageService } from '../core/language';
import { LanguageSwitcher } from '../shared/language-switcher/language-switcher';
import { TokenRequestsPanel } from '../shared/token-requests/token-requests';

@Component({
  selector: 'app-requests-page',
  imports: [RouterLink, LanguageSwitcher, TokenRequestsPanel],
  templateUrl: './requests-page.html',
  styleUrl: './requests-page.css',
})
export class RequestsPage {
  private auth = inject(AuthService);
  private router = inject(Router);
  readonly lang = inject(LanguageService);

  readonly userEmail = computed(() => this.auth.user()?.email ?? '');

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
