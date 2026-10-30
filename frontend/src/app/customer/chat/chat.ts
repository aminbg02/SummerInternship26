import { DecimalPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { AdminService } from '../../admin/admin-service';
import { AccountService } from '../../core/account-service';
import { AuthService } from '../../core/auth';
import { LanguageService } from '../../core/language';
import {
  AccountUsage,
  AdminCompany,
  ChatMessage,
  ConversationSummary,
  Provider,
  ProviderView,
} from '../../core/models';
import { roleHome } from '../../core/role-home';
import { ChatService } from './chat-service';
import { ChatComposer } from './composer/composer';
import { ChatHistory, RenameEvent } from './history/history';
import { ChatToolbar } from './toolbar/toolbar';
import { ChatTranscript } from './transcript/transcript';

const DEFAULT_TEMPERATURE = 0.2;
const DEFAULT_MAX_TOKENS = 1024;
const FALLBACK_MAX_TOKENS_CEILING = 4096;

const TICK_MS = 5_000;
const POLL_MS = 30_000;
const DEFAULT_COOLDOWN_S = 60;
const TOAST_MS = 5_000;

interface Cooldown {
  until: number;
}

@Component({
  selector: 'app-chat',
  imports: [DecimalPipe, ChatToolbar, ChatHistory, ChatTranscript, ChatComposer],
  templateUrl: './chat.html',
  styleUrl: './chat.css',
})
export class Chat implements OnInit, OnDestroy {
  private chat = inject(ChatService);
  private auth = inject(AuthService);
  private account = inject(AccountService);
  private admin = inject(AdminService);
  private router = inject(Router);
  readonly lang = inject(LanguageService);

  readonly providers = signal<Provider[]>([]);
  readonly companies = signal<AdminCompany[]>([]);
  readonly conversations = signal<ConversationSummary[]>([]);
  readonly messages = signal<ChatMessage[]>([]);
  readonly loading = signal(false);
  readonly banner = signal<string | null>(null);
  readonly uploadInfo = signal<string | null>(null);
  readonly toast = signal<string | null>(null);
  private toastTimer?: ReturnType<typeof setTimeout>;
  readonly usage = signal<AccountUsage | null>(null);

  readonly quotaLabel = computed(() => {
    const u = this.usage();
    if (u?.scope === 'company') {
      return this.lang.t('chat.quotaLabelCompany', { name: u.company?.name ?? 'company' });
    }
    return this.lang.t('chat.quotaLabel');
  });
  readonly conversationId = signal<number | null>(null);

  private readonly cooldowns = signal<Record<number, Cooldown>>({});
  private readonly now = signal(Date.now());
  private ticker?: ReturnType<typeof setInterval>;
  private poller?: ReturnType<typeof setInterval>;

  readonly userEmail = computed(() => this.auth.user()?.email ?? '');
  readonly isSuperAdmin = computed(() => this.auth.user()?.role === 'super_admin');
  readonly consoleHome = computed(() => {
    const role = this.auth.user()?.role;
    return role === 'super_admin' || role === 'company_admin' ? roleHome(role) : null;
  });
  readonly providerViews = computed<ProviderView[]>(() => {
    const t = this.now();
    const cds = this.cooldowns();
    return this.providers().map((p) => {
      const local = cds[p.id];
      const localBlocked = local != null && local.until > t;
      const serverBlocked = p.available === false;
      const available = !localBlocked && !serverBlocked;
      return { ...p, available };
    });
  });

  readonly selectedAvailable = computed(() => {
    const v = this.providerViews().find((p) => p.id === this.providerId());
    return v ? v.available : false;
  });

  readonly anyAvailable = computed(() => this.providerViews().some((p) => p.available));

  readonly companyId = signal<number | null>(null);

  readonly canSend = computed(
    () =>
      this.selectedAvailable() &&
      !this.loading() &&
      (!this.isSuperAdmin() || this.companyId() != null),
  );

  draft = '';

  readonly providerId = signal<number | null>(null);
  readonly temperature = signal(DEFAULT_TEMPERATURE);
  readonly maxTokens = signal(DEFAULT_MAX_TOKENS);

  readonly selectedProvider = computed(() =>
    this.providers().find((p) => p.id === this.providerId()),
  );

  readonly maxTokensCeiling = computed(
    () => this.selectedProvider()?.max_output_tokens ?? FALLBACK_MAX_TOKENS_CEILING,
  );

  ngOnInit(): void {
    this.loadProviders(true);
    this.refreshUsage();
    if (this.isSuperAdmin()) this.loadCompanies();
    else this.loadConversations();

    this.ticker = setInterval(() => this.now.set(Date.now()), TICK_MS);
    this.poller = setInterval(() => this.loadProviders(false), POLL_MS);
  }

  ngOnDestroy(): void {
    if (this.ticker) clearInterval(this.ticker);
    if (this.poller) clearInterval(this.poller);
    if (this.toastTimer) clearTimeout(this.toastTimer);
  }

  private loadProviders(initial: boolean): void {
    this.chat.listProviders().subscribe({
      next: (res) => {
        this.providers.set(res.providers);
        if (initial) {
          if (res.providers.length) {
            this.providerId.set(this.firstAvailableId() ?? res.providers[0].id);
            this.applyProviderDefaults();
          } else {
            this.banner.set(this.lang.t('chat.noModels'));
          }
        }
      },
      error: () => {
        if (initial) this.banner.set(this.lang.t('chat.loadModelsFailed'));
      },
    });
  }

  private loadCompanies(): void {
    this.admin.listCompanies().subscribe({
      next: (res) => {
        this.companies.set(res.companies);
        if (res.companies.length && this.companyId() == null) {
          this.companyId.set(res.companies[0].id);
          this.loadConversations();
        } else if (!res.companies.length) {
          this.banner.set(this.lang.t('chat.noCompanies'));
        }
      },
      error: () => this.banner.set(this.lang.t('chat.loadCompaniesFailed')),
    });
  }

  onCompanyChange(id: number | string | null): void {
    const next = id == null || id === '' ? null : Number(id);
    if (next === this.companyId()) return;
    this.companyId.set(next);
    this.conversationId.set(null);
    this.messages.set([]);
    this.uploadInfo.set(null);
    this.loadConversations();
    const name = this.companies().find((c) => c.id === next)?.name;
    this.banner.set(name ? this.lang.t('chat.nowAsking', { name }) : null);
  }

  private firstAvailableId(): number | null {
    return this.providerViews().find((p) => p.available)?.id ?? null;
  }

  private markUnavailable(id: number, seconds = DEFAULT_COOLDOWN_S): void {
    const until = Date.now() + seconds * 1000;
    this.cooldowns.update((m) => ({ ...m, [id]: { until } }));
  }

  private loadConversations(): void {
    this.chat.listConversations(this.companyId()).subscribe({
      next: (res) => this.conversations.set(res.conversations),
      error: () => {},
    });
  }

  newChat(): void {
    this.conversationId.set(null);
    this.messages.set([]);
    this.uploadInfo.set(null);
    this.banner.set(null);
  }

  openConversation(id: number): void {
    if (id === this.conversationId()) return;
    this.chat.getConversation(id, this.companyId()).subscribe({
      next: (res) => {
        this.conversationId.set(id);
        this.uploadInfo.set(null);
        this.banner.set(null);
        this.messages.set(
          res.messages.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            citations: m.sources,
            feedback: m.feedback ?? null,
          })),
        );
      },
      error: () => this.showToast(this.lang.t('chat.openConversationFailed')),
    });
  }

  rateMessage({ id, value }: { id: number; value: 'up' | 'down' }): void {
    const convoId = this.conversationId();
    if (convoId == null) return;

    const current = this.messages().find((m) => m.id === id)?.feedback ?? null;
    const next = current === value ? null : value;
    const setFeedback = (fb: 'up' | 'down' | null) =>
      this.messages.update((list) =>
        list.map((m) => (m.id === id ? { ...m, feedback: fb } : m)),
      );

    setFeedback(next);
    this.chat.setFeedback(convoId, id, next, this.companyId()).subscribe({
      error: () => {
        setFeedback(current);
        this.showToast(this.lang.t('chat.feedbackSaveFailed'));
      },
    });
  }

  renameConversation({ id, title }: RenameEvent): void {
    this.chat.renameConversation(id, title, this.companyId()).subscribe({
      next: (res) =>
        this.conversations.update((list) =>
          list.map((row) => (row.id === id ? { ...row, title: res.conversation.title } : row)),
        ),
      error: () => this.showToast(this.lang.t('chat.renameFailed')),
    });
  }

  deleteConversation(id: number): void {
    this.chat.deleteConversation(id, this.companyId()).subscribe({
      next: () => {
        this.conversations.update((list) => list.filter((c) => c.id !== id));
        if (this.conversationId() === id) this.newChat();
      },
      error: () => this.showToast(this.lang.t('chat.deleteFailed')),
    });
  }

  private showToast(message: string): void {
    this.toast.set(message);
    if (this.toastTimer) clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => this.toast.set(null), TOAST_MS);
  }

  dismissToast(): void {
    if (this.toastTimer) clearTimeout(this.toastTimer);
    this.toast.set(null);
  }

  private providerName(id: number | null | undefined): string {
    return this.providers().find((p) => p.id === id)?.display_name ?? 'That model';
  }

  private refreshUsage(): void {
    this.account.usage().subscribe({
      next: (u) => this.usage.set(u),
      error: () => {},
    });
  }

  onProviderChange(): void {
    this.applyProviderDefaults();
  }

  private applyProviderDefaults(): void {
    const p = this.selectedProvider();
    this.temperature.set(p?.default_temperature ?? DEFAULT_TEMPERATURE);
    this.maxTokens.set(
      Math.min(p?.max_output_tokens ?? DEFAULT_MAX_TOKENS, this.maxTokensCeiling()),
    );
  }

  send(): void {
    const question = this.draft.trim();
    if (!question || !this.canSend()) return;

    this.pushMessage({ role: 'user', content: question });
    this.draft = '';
    this.banner.set(null);
    this.loading.set(true);

    const isNewThread = this.conversationId() == null;

    this.chat
      .sendQuery(
        {
          question,
          provider_id: this.providerId()!,
          conversation_id: this.conversationId() ?? undefined,
          temperature: this.temperature(),
          max_tokens: this.maxTokens(),
          locale: this.lang.current(),
        },
        this.companyId(),
      )
      .subscribe({
        next: (res) => {
          this.loading.set(false);
          if (res.conversation_id) this.conversationId.set(res.conversation_id);
          this.pushMessage({
            role: 'assistant',
            content: res.answer ?? '',
            id: res.message_id,
            provider: res.provider,
            usage: res.usage,
            params: res.params,
            fellBack: res.fell_back,
            sources: res.chunks,
            citations: res.sources,
            feedback: null,
          });
          if (isNewThread) this.loadConversations();
          this.refreshUsage();
        },
        error: (err: HttpErrorResponse) => {
          this.loading.set(false);
          this.handleQueryError(err);
        },
      });
  }

  private handleQueryError(err: HttpErrorResponse): void {
    const body = (err.error ?? {}) as Record<string, unknown>;
    const code = body['error'] as string | undefined;
    if (body['reason']) console.debug('[provider down]', body['provider_id'], body['reason']);

    if (code === 'llm_call_failed' || code === 'rate_limited') {
      const providerId = body['provider_id'] as number | undefined;
      const retryAfter = body['retry_after'] as number | undefined;
      if (providerId != null) {
        this.markUnavailable(providerId, retryAfter ?? DEFAULT_COOLDOWN_S);
      }
      const genericFailure = this.lang.t('chat.genericFailure');
      this.showToast(genericFailure);
      this.pushMessage({ role: 'assistant', content: genericFailure, error: true });
      this.refreshUsage();
      return;
    }

    const message =
      code === 'quota_exceeded'
        ? body['scope'] === 'user'
          ? this.lang.t('chat.quotaExceededUser')
          : this.lang.t('chat.quotaExceededCompany')
        : code === 'admin_must_select_company'
          ? this.lang.t('chat.pickCompanyFirst')
          : err.status === 401 || err.status === 422
            ? this.lang.t('chat.sessionExpired')
            : this.lang.t('chat.somethingWrong');

    this.showToast(message);
    this.pushMessage({ role: 'assistant', content: message, error: true });
    this.refreshUsage();
  }

  uploadFile(file: File): void {
    this.uploadInfo.set(this.lang.t('chat.uploading', { name: file.name }));
    this.chat.upload(file, this.conversationId(), this.companyId()).subscribe({
      next: (r) => {
        this.uploadInfo.set(
          this.lang.t('chat.uploadStaged', { filename: r.filename, count: r.accepted_chunks }) +
            (r.redacted_chunks ? this.lang.t('chat.uploadRedacted', { count: r.redacted_chunks }) : '') +
            (r.blocked_chunks ? this.lang.t('chat.uploadBlocked', { count: r.blocked_chunks }) : '') +
            '.',
        );
      },
      error: () => this.uploadInfo.set(this.lang.t('chat.uploadFailed')),
    });
  }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }

  private pushMessage(m: ChatMessage): void {
    this.messages.update((list) => [...list, m]);
  }
}
