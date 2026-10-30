import { Component, inject, input, model, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AdminCompany, ProviderView } from '../../../core/models';
import { LanguageService } from '../../../core/language';
import { LanguageSwitcher } from '../../../shared/language-switcher/language-switcher';

@Component({
  selector: 'app-chat-toolbar',
  imports: [FormsModule, RouterLink, LanguageSwitcher],
  templateUrl: './toolbar.html',
  styleUrl: './toolbar.css',
})
export class ChatToolbar {
  readonly lang = inject(LanguageService);

  readonly userEmail = input<string>('');
  readonly consoleHome = input<string | null>(null);

  readonly isSuperAdmin = input<boolean>(false);
  readonly companies = input<AdminCompany[]>([]);
  readonly companyId = input<number | null>(null);
  readonly companyChange = output<number | string | null>();

  readonly providerViews = input<ProviderView[]>([]);
  readonly providerId = model<number | null>(null);
  readonly providerChange = output<void>();

  readonly temperature = model<number>(0.2);
  readonly maxTokens = model<number>(1024);
  readonly maxTokensCeiling = input<number>(4096);

  readonly logout = output<void>();
}
