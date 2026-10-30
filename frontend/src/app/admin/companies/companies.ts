import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  AdminCompany,
  CompanyIsolation,
  MovedUsers,
  QdrantPoolStatus,
} from '../../core/models';
import { LanguageService } from '../../core/language';
import { AdminService } from '../admin-service';

@Component({
  selector: 'app-companies-admin',
  imports: [FormsModule],
  templateUrl: './companies.html',
  styleUrl: './companies.css',
})
export class CompaniesAdmin implements OnInit {
  private admin = inject(AdminService);
  readonly lang = inject(LanguageService);

  readonly rows = signal<AdminCompany[]>([]);
  readonly error = signal<string | null>(null);
  readonly notice = signal<string | null>(null);
  readonly busy = signal(false);
  readonly savingId = signal<number | null>(null);

  readonly pool = signal<QdrantPoolStatus | null>(null);

  name = '';
  domain = '';
  dailyTokenLimit: number | null = null;
  isolation: CompanyIsolation = 'shared';

  caps: Record<number, number | null> = {};
  domains: Record<number, string> = {};

  ngOnInit(): void {
    this.reload();
    this.reloadPool();
  }

  reload(): void {
    this.admin.listCompanies().subscribe({
      next: (r) => {
        this.rows.set(r.companies);
        this.caps = {};
        this.domains = {};
        for (const c of r.companies) {
          this.caps[c.id] = c.daily_token_limit ?? null;
          this.domains[c.id] = c.domain ?? '';
        }
      },
      error: () => this.error.set('Failed to load companies.'),
    });
  }

  reloadPool(): void {
    this.admin.qdrantPool().subscribe({
      next: (p) => {
        this.pool.set(p);
        if (!p.available && this.isolation === 'dedicated') this.isolation = 'shared';
      },
      error: () => this.pool.set(null),
    });
  }

  dedicatedUnavailable(): boolean {
    const p = this.pool();
    return p !== null && !p.available;
  }

  dedicatedHint(): string {
    const p = this.pool();
    if (p === null) return '';
    if (p.configured === 0) {
      return 'No dedicated instances are configured on this deployment.';
    }
    if (p.free === 0) {
      return `All ${p.configured} dedicated instances are assigned.`;
    }
    return `${p.free} of ${p.configured} dedicated instances free.`;
  }

  private normalise(v: number | null | undefined): number | null {
    if (v === null || v === undefined || (v as unknown as string) === '') return null;
    const n = Number(v);
    return Number.isFinite(n) && n > 0 ? n : null;
  }

  private cleanDomain(v: string | null | undefined): string {
    return (v ?? '').trim().toLowerCase();
  }

  capChanged(c: AdminCompany): boolean {
    return this.normalise(this.caps[c.id]) !== this.normalise(c.daily_token_limit);
  }

  domainChanged(c: AdminCompany): boolean {
    return this.cleanDomain(this.domains[c.id]) !== this.cleanDomain(c.domain);
  }

  rowChanged(c: AdminCompany): boolean {
    return this.capChanged(c) || this.domainChanged(c);
  }

  saveRow(c: AdminCompany): void {
    this.error.set(null);
    this.notice.set(null);

    const cap = this.normalise(this.caps[c.id]);
    const domain = this.cleanDomain(this.domains[c.id]);
    const domainMoved = this.domainChanged(c);

    if (cap !== null && cap < 0) {
      this.error.set('A cap cannot be negative.');
      return;
    }

    if (domainMoved && c.domain) {
      const ok = confirm(
        `Change ${c.name}'s domain from ${c.domain} to ${domain || '(none)'}?\n\n` +
          `Everyone at ${c.name} whose email is @${c.domain} will be moved to ` +
          `@${domain || '(none)'}. They will have to sign in with the new address ` +
          `from now on. Their password does not change.`,
      );
      if (!ok) return;
    }

    const body: Partial<AdminCompany> = {};
    if (this.capChanged(c)) body.daily_token_limit = cap;
    if (domainMoved) body.domain = domain || null;

    this.savingId.set(c.id);
    this.admin.updateCompany(c.id, body).subscribe({
      next: (r) => {
        this.savingId.set(null);
        this.rows.update((rows) =>
          rows.map((row) => (row.id === c.id ? r.company : row)),
        );
        this.caps[c.id] = r.company.daily_token_limit ?? null;
        this.domains[c.id] = r.company.domain ?? '';
        this.notice.set(this.describeSave(r.company, cap, r.users));
      },
      error: (err) => {
        this.savingId.set(null);
        const code = err?.error?.error;
        this.error.set(
          code === 'domain_taken'
            ? 'That email domain already belongs to another company.'
            : `Could not update ${c.name} (${code ?? 'unknown error'}).`,
        );
      },
    });
  }

  private describeSave(
    company: AdminCompany,
    cap: number | null,
    users?: MovedUsers,
  ): string {
    const parts: string[] = [];

    const moved = users?.moved?.length ?? 0;
    const skipped = users?.skipped?.length ?? 0;
    if (moved) {
      parts.push(
        `${moved} user${moved === 1 ? '' : 's'} moved to @${company.domain} — they sign in with the new address now.`,
      );
    }
    if (skipped) {
      parts.push(
        `${skipped} left as ${skipped === 1 ? 'it was' : 'they were'} (that address is already taken).`,
      );
    }
    if (!parts.length) {
      parts.push(
        cap === null
          ? `${company.name} is now uncapped.`
          : `${company.name} capped at ${cap.toLocaleString()} tokens/day (shared by all its users).`,
      );
    }
    return parts.join(' ');
  }

  private describeCreate(company: AdminCompany): string {
    const where =
      company.isolation === 'dedicated'
        ? `on its own Qdrant instance (${company.qdrant_url})`
        : 'on the shared Qdrant instance';
    return `Created ${company.name} (${company.domain ?? 'no domain'}) — knowledge base ${where}.`;
  }

  create(): void {
    this.error.set(null);
    this.notice.set(null);
    if (!this.name.trim()) {
      this.error.set('Enter a company name.');
      return;
    }
    this.busy.set(true);
    this.admin
      .createCompany({
        name: this.name.trim(),
        domain: this.domain.trim() || null,
        daily_token_limit: this.dailyTokenLimit,
        isolation: this.isolation,
      })
      .subscribe({
        next: (r) => {
          this.busy.set(false);
          if (r.warning === 'company_created_without_collection') {
            this.error.set(
              `${r.company.name} was created, but its knowledge base could not be set up on ` +
                `${r.company.qdrant_url ?? 'the shared Qdrant instance'}. Check that the ` +
                `container is running (docker compose up -d), then restart the backend — ` +
                `it retries on boot.`,
            );
          } else {
            this.notice.set(this.describeCreate(r.company));
          }
          this.name = '';
          this.domain = '';
          this.dailyTokenLimit = null;
          this.isolation = 'shared';
          this.reload();
          this.reloadPool();
        },
        error: (err) => {
          this.busy.set(false);
          const code = err?.error?.error;
          this.error.set(
            code === 'domain_taken'
              ? 'That email domain is already used by another company.'
              : code === 'name_taken'
                ? 'That company name already exists.'
                : code === 'no_dedicated_instance_available'
                  ? (err?.error?.detail ??
                     'No dedicated Qdrant instance is free.') +
                    ' Add one to docker-compose.yml and QDRANT_DEDICATED_URLS, or create it as shared.'
                  : `Could not create company (${code ?? 'unknown error'}).`,
          );
          this.reloadPool();
        },
      });
  }
}
