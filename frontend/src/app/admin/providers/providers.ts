import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AdminProvider } from '../../core/models';
import { LanguageService } from '../../core/language';
import { AdminService, ProviderPayload } from '../admin-service';

interface ProviderForm extends ProviderPayload {
  id: number | null;
}

function blankForm(): ProviderForm {
  return {
    id: null,
    display_name: '',
    provider_key: 'groq',
    base_url: '',
    model_name: '',
    api_key: '',
    enabled: true,
    is_free: true,
    rate_limit_rpm: null,
    rate_limit_rpd: null,
    priority: 100,
    default_temperature: null,
    max_output_tokens: null,
  };
}

@Component({
  selector: 'app-providers-admin',
  imports: [FormsModule],
  templateUrl: './providers.html',
  styleUrl: './providers.css',
})
export class ProvidersAdmin implements OnInit {
  private admin = inject(AdminService);
  readonly lang = inject(LanguageService);

  readonly providers = signal<AdminProvider[]>([]);
  readonly error = signal<string | null>(null);
  readonly showForm = signal(false);
  readonly testResults = signal<Record<number, string>>({});

  form: ProviderForm = blankForm();

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.admin.listProviders().subscribe({
      next: (res) => this.providers.set(res.providers),
      error: () => this.error.set('Failed to load providers.'),
    });
  }

  startCreate(): void {
    this.form = blankForm();
    this.showForm.set(true);
  }

  startEdit(p: AdminProvider): void {
    this.form = {
      id: p.id,
      display_name: p.display_name,
      provider_key: p.provider_key,
      base_url: p.base_url ?? '',
      model_name: p.model_name,
      api_key: '',
      enabled: p.enabled,
      is_free: p.is_free,
      rate_limit_rpm: p.rate_limit_rpm,
      rate_limit_rpd: p.rate_limit_rpd,
      priority: p.priority,
      default_temperature: p.default_temperature,
      max_output_tokens: p.max_output_tokens,
    };
    this.showForm.set(true);
  }

  cancel(): void {
    this.showForm.set(false);
    this.form = blankForm();
  }

  save(): void {
    const f = this.form;
    const body: ProviderPayload = {
      display_name: f.display_name,
      provider_key: f.provider_key,
      base_url: f.base_url ? f.base_url : null,
      model_name: f.model_name,
      enabled: f.enabled,
      is_free: f.is_free,
      rate_limit_rpm: f.rate_limit_rpm,
      rate_limit_rpd: f.rate_limit_rpd,
      priority: f.priority,
      default_temperature: f.default_temperature,
      max_output_tokens: f.max_output_tokens,
    };
    if (f.api_key) body.api_key = f.api_key;

    const done = {
      next: () => {
        this.showForm.set(false);
        this.form = blankForm();
        this.load();
      },
      error: () => this.error.set('Save failed — check the fields and try again.'),
    };

    if (f.id == null) {
      this.admin.createProvider(body).subscribe(done);
    } else {
      this.admin.updateProvider(f.id, body).subscribe(done);
    }
  }

  toggleEnabled(p: AdminProvider): void {
    this.admin.updateProvider(p.id, { enabled: !p.enabled }).subscribe({
      next: () => this.load(),
      error: () => this.error.set('Could not update.'),
    });
  }

  remove(p: AdminProvider): void {
    if (!confirm(`Delete provider “${p.display_name}”?`)) return;
    this.admin.deleteProvider(p.id).subscribe({
      next: () => this.load(),
      error: () => this.error.set('Delete failed.'),
    });
  }

  test(p: AdminProvider): void {
    this.setTestResult(p.id, 'testing…');
    this.admin.testProvider(p.id).subscribe({
      next: (r) =>
        this.setTestResult(p.id, r.ok ? `✓ ${r.result?.content ?? 'ok'}` : `✗ ${r.detail ?? 'failed'}`),
      error: (err) => this.setTestResult(p.id, `✗ ${err?.error?.error ?? 'failed'}`),
    });
  }

  private setTestResult(id: number, msg: string): void {
    this.testResults.update((m) => ({ ...m, [id]: msg }));
  }
}
