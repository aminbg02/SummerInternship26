import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { LANGUAGE_NAMES, LanguageService } from '../../core/language';

@Component({
  selector: 'app-language-switcher',
  imports: [FormsModule],
  templateUrl: './language-switcher.html',
  styleUrl: './language-switcher.css',
})
export class LanguageSwitcher {
  readonly lang = inject(LanguageService);
  readonly names = LANGUAGE_NAMES;
}
