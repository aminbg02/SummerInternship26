import { Component, computed, inject } from '@angular/core';
import { SlicePipe, UpperCasePipe } from '@angular/common';
import { RouterLink, RouterLinkActive, RouterOutlet, Router } from '@angular/router';

import { AuthService } from '../core/auth';
import { LanguageService } from '../core/language';
import { LanguageSwitcher } from '../shared/language-switcher/language-switcher';

@Component({
  selector: 'app-admin',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, SlicePipe, UpperCasePipe, LanguageSwitcher],
  templateUrl: './admin.html',
  styleUrl: './admin.css',
})
export class Admin {
  private auth = inject(AuthService);
  private router = inject(Router);
  readonly lang = inject(LanguageService);

  readonly userEmail = computed(() => this.auth.user()?.email ?? '');

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
