import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AdminCompany, AdminPiiRule } from '../../core/models';
import { LanguageService } from '../../core/language';
import { AdminService, CreatePiiRulePayload, PiiRulePayload } from '../admin-service';

interface PiiRuleForm {
  id: number | null;
  entity_name: string;
  pattern: string;
  score: number;
  enabled: boolean;
  companyIds: number[];
}

function blankForm(): PiiRuleForm {
  return { id: null, entity_name: '', pattern: '', score: 0.85, enabled: true, companyIds: [] };
}

type BuilderCharType = 'digits' | 'letters' | 'alnum';

interface PreviewSegment {
  text: string;
  match: boolean;
}

function escapeRegexLiteral(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

@Component({
  selector: 'app-pii-rules-admin',
  imports: [FormsModule],
  templateUrl: './pii-rules.html',
  styleUrl: './pii-rules.css',
})
export class PiiRulesAdmin implements OnInit {
  private admin = inject(AdminService);
  readonly lang = inject(LanguageService);

  readonly rules = signal<AdminPiiRule[]>([]);
  readonly companies = signal<AdminCompany[]>([]);
  readonly error = signal<string | null>(null);
  readonly showForm = signal(false);

  form: PiiRuleForm = blankForm();

  builderMode: 'simple' | 'advanced' = 'simple';
  builderPrefix = '';
  builderCharType: BuilderCharType = 'digits';
  builderCount = 6;
  builderSuffix = '';

  testText = '';

  ngOnInit(): void {
    this.load();
    this.admin.listCompanies().subscribe({
      next: (res) => this.companies.set(res.companies),
      error: () => this.error.set('Failed to load companies.'),
    });
  }

  load(): void {
    this.admin.listPiiRules().subscribe({
      next: (res) => this.rules.set(res.rules),
      error: () => this.error.set('Failed to load PII rules.'),
    });
  }

  companyName(companyId: number | null): string {
    if (companyId == null) return this.lang.t('piiRules.global');
    return this.companies().find((c) => c.id === companyId)?.name ?? `#${companyId}`;
  }

  startCreate(): void {
    this.form = blankForm();
    this.builderMode = 'simple';
    this.builderPrefix = '';
    this.builderCharType = 'digits';
    this.builderCount = 6;
    this.builderSuffix = '';
    this.testText = '';
    this.updateGeneratedPattern();
    this.showForm.set(true);
  }

  startEdit(r: AdminPiiRule): void {
    this.form = {
      id: r.id,
      entity_name: r.entity_name,
      pattern: r.pattern,
      score: r.score,
      enabled: r.enabled,
      companyIds: r.company_id == null ? [] : [r.company_id],
    };
    this.builderMode = 'advanced';
    this.testText = '';
    this.showForm.set(true);
  }

  cancel(): void {
    this.showForm.set(false);
    this.form = blankForm();
  }

  toggleCompanyChecked(companyId: number, checked: boolean): void {
    const ids = new Set(this.form.companyIds);
    if (checked) ids.add(companyId);
    else ids.delete(companyId);
    this.form.companyIds = [...ids];
  }

  get editCompanyId(): number | null {
    return this.form.companyIds.length > 0 ? this.form.companyIds[0] : null;
  }
  set editCompanyId(value: number | null) {
    this.form.companyIds = value == null ? [] : [value];
  }

  setBuilderMode(mode: 'simple' | 'advanced'): void {
    this.builderMode = mode;
    if (mode === 'simple') this.updateGeneratedPattern();
  }

  updateGeneratedPattern(): void {
    const charClass: Record<BuilderCharType, string> = {
      digits: '\\d',
      letters: '[A-Za-z]',
      alnum: '[A-Za-z0-9]',
    };
    const count = Math.max(1, Math.floor(this.builderCount) || 1);
    const prefix = escapeRegexLiteral(this.builderPrefix);
    const suffix = escapeRegexLiteral(this.builderSuffix);
    this.form.pattern = `\\b${prefix}${charClass[this.builderCharType]}{${count}}${suffix}\\b`;
  }

  get testPreview(): PreviewSegment[] | null {
    if (!this.testText || !this.form.pattern) return null;
    let re: RegExp;
    try {
      re = new RegExp(this.form.pattern, 'g');
    } catch {
      return null;
    }
    const segments: PreviewSegment[] = [];
    let lastEnd = 0;
    for (const m of this.testText.matchAll(re)) {
      if (m.index == null || m[0] === '') continue;
      if (m.index > lastEnd) segments.push({ text: this.testText.slice(lastEnd, m.index), match: false });
      segments.push({ text: m[0], match: true });
      lastEnd = m.index + m[0].length;
    }
    if (lastEnd < this.testText.length) segments.push({ text: this.testText.slice(lastEnd), match: false });
    return segments;
  }

  save(): void {
    const f = this.form;

    const done = {
      next: () => {
        this.showForm.set(false);
        this.form = blankForm();
        this.error.set(null);
        this.load();
      },
      error: (err: { error?: { error?: string; detail?: string } }) =>
        this.error.set(err?.error?.detail ?? err?.error?.error ?? 'Save failed — check the fields and try again.'),
    };

    if (f.id == null) {
      const body: CreatePiiRulePayload = {
        entity_name: f.entity_name,
        pattern: f.pattern,
        score: f.score,
        enabled: f.enabled,
        company_ids: f.companyIds,
      };
      this.admin.createPiiRule(body).subscribe(done);
    } else {
      const body: PiiRulePayload = {
        entity_name: f.entity_name,
        pattern: f.pattern,
        score: f.score,
        enabled: f.enabled,
        company_id: f.companyIds[0] ?? null,
      };
      this.admin.updatePiiRule(f.id, body).subscribe(done);
    }
  }

  toggleEnabled(r: AdminPiiRule): void {
    this.admin.updatePiiRule(r.id, { enabled: !r.enabled }).subscribe({
      next: () => this.load(),
      error: () => this.error.set('Could not update.'),
    });
  }

  remove(r: AdminPiiRule): void {
    if (!confirm(`Delete PII rule "${r.entity_name}"?`)) return;
    this.admin.deletePiiRule(r.id).subscribe({
      next: () => this.load(),
      error: () => this.error.set('Delete failed.'),
    });
  }
}
