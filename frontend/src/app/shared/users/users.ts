import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../core/auth';
import { LanguageService } from '../../core/language';
import { ManagedUser, Role } from '../../core/models';
import { UsersService } from '../../core/users-service';

@Component({
  selector: 'app-users-manage',
  imports: [FormsModule],
  templateUrl: './users.html',
  styleUrl: './users.css',
})
export class UsersManage implements OnInit {
  private users = inject(UsersService);
  private auth = inject(AuthService);
  readonly lang = inject(LanguageService);

  readonly rows = signal<ManagedUser[]>([]);
  readonly companyLimits = signal<Record<string, number | null>>({});
  readonly companyAllocated = signal<Record<string, number>>({});
  readonly error = signal<string | null>(null);
  readonly notice = signal<string | null>(null);
  readonly busy = signal(false);

  readonly isSuperAdmin = computed(() => this.auth.user()?.role === 'super_admin');

  readonly companyPool = computed<number | null | undefined>(() => {
    const me = this.auth.user();
    if (!me || me.company_id === null) return undefined;
    return this.companyLimits()[String(me.company_id)];
  });

  readonly companyAllocatedForMe = computed<number>(() => {
    const me = this.auth.user();
    if (!me || me.company_id === null) return 0;
    return this.companyAllocated()[String(me.company_id)] ?? 0;
  });

  companyPoolLabel(): string {
    const pool = this.companyPool();
    if (pool == null) return this.lang.t('users.companyPoolUncapped');
    const allocated = this.companyAllocatedForMe();
    const remaining = Math.max(pool - allocated, 0);
    return this.lang.t('users.companyPoolBreakdown', {
      pool: pool.toLocaleString(),
      allocated: allocated.toLocaleString(),
      remaining: remaining.toLocaleString(),
    });
  }

  readonly editingCap = signal<number | null>(null);
  capDraft: number | null = null;

  canSetCap(u: ManagedUser): boolean {
    const me = this.auth.user();
    if (!me || u.role === 'super_admin') return false;
    return this.isSuperAdmin() || (u.role === 'customer' && u.company_id === me.company_id);
  }

  ceilingFor(u: ManagedUser): number | null {
    if (u.company_id === null) return null;
    const pool = this.companyLimits()[String(u.company_id)] ?? null;
    if (pool == null) return null;
    const totalAllocated = this.companyAllocated()[String(u.company_id)] ?? 0;
    const others = totalAllocated - (u.daily_token_limit ?? 0);
    return Math.max(pool - others, 0);
  }

  capLabel(u: ManagedUser): string {
    if (u.role === 'super_admin') return this.lang.t('users.uncapped');
    if (u.daily_token_limit === null) {
      return this.lang.t('users.defaultSuffix', { n: u.effective_token_limit.toLocaleString() });
    }
    return u.daily_token_limit === 0
      ? this.lang.t('users.unlimited')
      : u.daily_token_limit.toLocaleString();
  }

  startEditCap(u: ManagedUser): void {
    this.error.set(null);
    this.notice.set(null);
    this.editingCap.set(u.id);
    this.capDraft = u.daily_token_limit;
  }

  cancelEditCap(): void {
    this.editingCap.set(null);
    this.capDraft = null;
  }

  saveCap(u: ManagedUser): void {
    const limit = this.capDraft;
    if (limit !== null && (!Number.isInteger(limit) || limit < 0)) {
      this.error.set('Enter a whole number of tokens, or leave blank to use the default.');
      return;
    }

    this.error.set(null);
    this.notice.set(null);
    this.busy.set(true);
    this.users.setTokenLimit(u.id, limit).subscribe({
      next: (r) => {
        this.busy.set(false);
        this.cancelEditCap();
        this.notice.set(
          limit === null
            ? `${r.user.email} now uses the default cap (${r.user.effective_token_limit.toLocaleString()} tokens/day).`
            : `${r.user.email} capped at ${limit.toLocaleString()} tokens/day.`,
        );
        this.reload();
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(this.explain(err?.error?.error, err?.error));
      },
    });
  }

  canDelete(u: ManagedUser): boolean {
    const me = this.auth.user();
    if (!me || u.id === me.id) return false;
    return this.isSuperAdmin() || u.role === 'customer';
  }

  remove(u: ManagedUser): void {
    if (!confirm(`Delete ${u.email}? Their chat history is removed; usage history is kept.`)) {
      return;
    }
    this.error.set(null);
    this.notice.set(null);
    this.users.deleteUser(u.id).subscribe({
      next: () => {
        this.notice.set(`Deleted ${u.email}.`);
        this.reload();
      },
      error: (err) => {
        const code = err?.error?.error;
        this.error.set(
          code === 'cannot_delete_self'
            ? 'You cannot delete the account you are signed in as.'
            : code === 'forbidden'
              ? 'You are not allowed to delete this user.'
              : `Could not delete user (${code ?? 'unknown error'}).`,
        );
      },
    });
  }

  email = '';
  password = '';
  role: Role = 'customer';
  newCap: number | null = null;

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.users.listUsers().subscribe({
      next: (r) => {
        this.rows.set(r.users);
        this.companyLimits.set(r.company_limits ?? {});
        this.companyAllocated.set(r.company_allocated ?? {});
      },
      error: () => this.error.set('Failed to load users.'),
    });
  }

  create(): void {
    this.error.set(null);
    this.notice.set(null);
    if (!this.email.trim() || this.password.length < 6) {
      this.error.set('Enter an email and a password of at least 6 characters.');
      return;
    }
    const creatingSuperAdmin = this.isSuperAdmin() && this.role === 'super_admin';
    const daily_token_limit = creatingSuperAdmin ? null : this.newCap;
    if (daily_token_limit !== null &&
        (!Number.isInteger(daily_token_limit) || daily_token_limit < 0)) {
      this.error.set('The token cap must be a whole number, or blank for the default.');
      return;
    }

    this.busy.set(true);
    const body = this.isSuperAdmin()
      ? { email: this.email.trim(), password: this.password, role: this.role }
      : { email: this.email.trim(), password: this.password };
    this.users.createUser({
      ...body,
      ...(daily_token_limit === null ? {} : { daily_token_limit }),
    }).subscribe({
      next: (r) => {
        this.busy.set(false);
        this.notice.set(`Created ${r.user.email} (${r.user.role}).`);
        this.email = '';
        this.password = '';
        this.role = 'customer';
        this.newCap = null;
        this.reload();
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(this.explain(err?.error?.error, err?.error));
      },
    });
  }

  private explain(code: string | undefined, body: any): string {
    switch (code) {
      case 'email_taken':
        return 'That email is already registered.';
      case 'invalid_email':
        return 'That does not look like a valid email address.';
      case 'weak_password':
        return 'Password must be at least 6 characters.';
      case 'forbidden_role':
        return 'You can only create customer accounts.';
      case 'email_domain_mismatch':
        return `The email domain must match your company (${body?.expected ?? ''}).`;
      case 'cap_exceeds_company_limit': {
        const pool = Number(body?.company_limit ?? 0).toLocaleString();
        return body?.requested === 'unlimited'
          ? `This company has a ${pool} token/day pool, so a user cannot be uncapped. Enter a number up to ${pool}.`
          : `That is above the company's ${pool} token/day pool. Enter a number up to ${pool}.`;
      }
      case 'allocation_exceeds_company_limit': {
        const remaining = Number(body?.remaining ?? 0).toLocaleString();
        const allocated = Number(body?.already_allocated ?? 0).toLocaleString();
        return `Only ${remaining} tokens/day are left in the company pool (${allocated} already allocated to other customers). Enter a number up to ${remaining}, or lower another customer's cap first.`;
      }
      case 'super_admin_not_capped':
        return 'Super admins are never capped, so they cannot be given a token limit.';
      case 'invalid_token_limit':
        return 'The token cap must be a whole number of tokens, or blank for the default.';
      case 'missing_field':
        return 'No token cap was sent.';
      case 'user_not_found':
        return 'That user no longer exists.';
      case 'forbidden':
        return 'You are not allowed to do that.';
      default:
        return `Request failed (${code ?? 'unknown error'}).`;
    }
  }
}
