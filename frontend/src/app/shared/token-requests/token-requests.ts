import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../core/auth';
import { LanguageService } from '../../core/language';
import { TokenRequest } from '../../core/models';
import { TokenRequestsService } from '../../core/token-requests-service';

@Component({
  selector: 'app-token-requests',
  imports: [FormsModule],
  templateUrl: './token-requests.html',
  styleUrl: './token-requests.css',
})
export class TokenRequestsPanel implements OnInit {
  private requests = inject(TokenRequestsService);
  private auth = inject(AuthService);
  readonly lang = inject(LanguageService);

  readonly rows = signal<TokenRequest[]>([]);
  readonly error = signal<string | null>(null);
  readonly notice = signal<string | null>(null);
  readonly busy = signal(false);

  private readonly myId = computed(() => this.auth.user()?.id ?? null);

  readonly canCreate = computed(() => this.auth.user()?.role !== 'super_admin');

  readonly isCompanyAdmin = computed(() => this.auth.user()?.role === 'company_admin');

  readonly canReview = computed(() => {
    const role = this.auth.user()?.role;
    return role === 'company_admin' || role === 'super_admin';
  });

  readonly lede = computed(() => {
    const role = this.auth.user()?.role;
    if (role === 'company_admin') return this.lang.t('tokenRequests.ledeCompanyAdmin');
    if (role === 'super_admin') return this.lang.t('tokenRequests.ledeSuperAdmin');
    return this.lang.t('tokenRequests.ledeCustomer');
  });

  readonly formLabel = computed(() =>
    this.isCompanyAdmin()
      ? this.lang.t('tokenRequests.formLabelCompany')
      : this.lang.t('tokenRequests.formLabelUser'),
  );

  readonly limitPlaceholder = computed(() =>
    this.isCompanyAdmin()
      ? this.lang.t('tokenRequests.limitPlaceholderCompany')
      : this.lang.t('tokenRequests.limitPlaceholder'),
  );

  readonly reviewable = computed(() =>
    this.rows().filter((r) => r.status === 'pending' && r.requester_id !== this.myId()),
  );

  readonly myRequests = computed(() =>
    this.rows().filter((r) => r.requester_id === this.myId()),
  );

  requestedLimit: number | null = null;
  reason = '';

  readonly rejectingId = signal<number | null>(null);
  rejectReasonDraft = '';

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.requests.list().subscribe({
      next: (r) => this.rows.set(r.requests),
      error: () => this.error.set('Failed to load token requests.'),
    });
  }

  scopeLabel(r: TokenRequest): string {
    return r.scope === 'company' ? this.lang.t('tokenRequests.scopeCompany') : this.lang.t('tokenRequests.scopeUser');
  }

  requestedLabel(r: TokenRequest): string {
    if (r.scope === 'company') {
      return `+${r.requested_limit.toLocaleString()}`;
    }
    return r.requested_limit === 0
      ? this.lang.t('tokenRequests.unlimited')
      : r.requested_limit.toLocaleString();
  }

  statusLabel(r: TokenRequest): string {
    switch (r.status) {
      case 'approved':
        return this.lang.t('tokenRequests.statusApproved');
      case 'rejected':
        return this.lang.t('tokenRequests.statusRejected');
      default:
        return this.lang.t('tokenRequests.statusPending');
    }
  }

  filedAt(r: TokenRequest): string {
    return r.created_at ? new Date(r.created_at).toLocaleString() : '';
  }

  create(): void {
    this.error.set(null);
    this.notice.set(null);

    const limit = this.requestedLimit;
    if (limit === null || !Number.isInteger(limit) || limit < 0) {
      this.error.set(
        this.isCompanyAdmin()
          ? 'Enter a whole number of additional tokens per day.'
          : 'Enter a whole number of tokens (0 for unlimited).',
      );
      return;
    }
    if (!this.reason.trim()) {
      this.error.set('Tell your admin why you need more tokens.');
      return;
    }

    this.busy.set(true);
    this.requests.create({ requested_limit: limit, reason: this.reason.trim() }).subscribe({
      next: () => {
        this.busy.set(false);
        this.notice.set('Request submitted.');
        this.requestedLimit = null;
        this.reason = '';
        this.reload();
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(this.explain(err?.error?.error, err?.error));
      },
    });
  }

  approve(r: TokenRequest): void {
    this.error.set(null);
    this.notice.set(null);
    this.busy.set(true);
    this.requests.decide(r.id, { status: 'approved' }).subscribe({
      next: () => {
        this.busy.set(false);
        this.notice.set(`Approved ${r.requester_email ?? 'the request'}.`);
        this.reload();
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(this.explain(err?.error?.error, err?.error));
      },
    });
  }

  startReject(r: TokenRequest): void {
    this.error.set(null);
    this.notice.set(null);
    this.rejectingId.set(r.id);
    this.rejectReasonDraft = '';
  }

  cancelReject(): void {
    this.rejectingId.set(null);
    this.rejectReasonDraft = '';
  }

  confirmReject(r: TokenRequest): void {
    if (!this.rejectReasonDraft.trim()) {
      this.error.set('A reason is required to reject a request.');
      return;
    }
    this.error.set(null);
    this.notice.set(null);
    this.busy.set(true);
    this.requests
      .decide(r.id, { status: 'rejected', decision_reason: this.rejectReasonDraft.trim() })
      .subscribe({
        next: () => {
          this.busy.set(false);
          this.notice.set(`Rejected ${r.requester_email ?? 'the request'}.`);
          this.cancelReject();
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
      case 'missing_field':
        return body?.field === 'decision_reason'
          ? 'A reason is required to reject a request.'
          : body?.field === 'reason'
            ? 'Tell your admin why you need more tokens.'
            : 'A required field was missing.';
      case 'invalid_requested_limit':
        return 'Enter a whole number of tokens (0 for unlimited).';
      case 'request_already_pending':
        return 'You already have a request awaiting a decision.';
      case 'request_already_decided':
        return 'That request has already been decided.';
      case 'cap_exceeds_company_limit': {
        const pool = Number(body?.company_limit ?? 0).toLocaleString();
        return body?.requested === 'unlimited'
          ? `This company has a ${pool} token/day pool, so this request cannot be granted unlimited. Reject it and ask for a number up to ${pool}.`
          : `That is above the company's ${pool} token/day pool (it may have changed since the request was filed). Reject it and ask for a number up to ${pool}.`;
      }
      case 'allocation_exceeds_company_limit': {
        const remaining = Number(body?.remaining ?? 0).toLocaleString();
        return `Only ${remaining} tokens/day are left in the company pool. Reject this request, or free up room by lowering another customer's cap first.`;
      }
      case 'forbidden':
        return 'You are not allowed to do that.';
      case 'request_not_found':
        return 'That request no longer exists.';
      default:
        return `Request failed (${code ?? 'unknown error'}).`;
    }
  }
}
