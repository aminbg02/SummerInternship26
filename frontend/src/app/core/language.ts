import { Injectable, signal } from '@angular/core';

import { Lang, TRANSLATIONS } from './i18n/translations';

const LANG_KEY = 'orange_lang';
const SUPPORTED: Lang[] = ['en', 'fr', 'es', 'pl'];

export const LANGUAGE_NAMES: Record<Lang, string> = {
  en: 'English',
  fr: 'Français',
  es: 'Español',
  pl: 'Polski',
};

@Injectable({ providedIn: 'root' })
export class LanguageService {
  readonly supported = SUPPORTED;
  readonly current = signal<Lang>(readStoredLang());

  constructor() {
    document.documentElement.lang = this.current();
  }

  set(lang: Lang): void {
    localStorage.setItem(LANG_KEY, lang);
    this.current.set(lang);
    document.documentElement.lang = lang;
  }

  t(key: string, params?: Record<string, string | number>): string {
    let text = lookup(TRANSLATIONS[this.current()], key) ?? lookup(TRANSLATIONS.en, key) ?? key;
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        text = text.replace(`{{${k}}}`, String(v));
      }
    }
    return text;
  }
}

function lookup(dict: any, key: string): string | undefined {
  let node = dict;
  for (const part of key.split('.')) {
    if (node == null) return undefined;
    node = node[part];
  }
  return typeof node === 'string' ? node : undefined;
}

function readStoredLang(): Lang {
  const raw = localStorage.getItem(LANG_KEY);
  return raw && (SUPPORTED as string[]).includes(raw) ? (raw as Lang) : 'en';
}
