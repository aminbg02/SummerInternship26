import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AdminCompany, Deletion, Ingestion, KbDocumentContent } from '../../core/models';
import { LanguageService } from '../../core/language';
import { AdminService } from '../admin-service';

@Component({
  selector: 'app-kb-admin',
  imports: [FormsModule],
  templateUrl: './kb.html',
  styleUrl: './kb.css',
})
export class KbAdmin implements OnInit {
  private admin = inject(AdminService);
  readonly lang = inject(LanguageService);

  readonly companies = signal<AdminCompany[]>([]);
  readonly ingestions = signal<Ingestion[]>([]);
  readonly deletions = signal<Deletion[]>([]);
  readonly result = signal<string | null>(null);
  readonly error = signal<string | null>(null);
  readonly busy = signal(false);
  readonly removingId = signal<number | null>(null);

  readonly removedDocIds = computed(
    () => new Set(this.deletions().map((d) => d.document_id).filter((id): id is number => id != null)),
  );

  readonly preview = signal<KbDocumentContent | null>(null);
  readonly previewingId = signal<number | null>(null);
  readonly previewError = signal<string | null>(null);

  companyId: number | null = null;

  ngOnInit(): void {
    this.admin.listCompanies().subscribe({
      next: (r) => {
        this.companies.set(r.companies);
        if (r.companies.length) {
          this.companyId = r.companies[0].id;
          this.loadHistory();
        }
      },
      error: () => this.error.set('Failed to load companies.'),
    });
  }

  onCompanyChange(): void {
    this.result.set(null);
    this.closePreview();
    this.loadHistory();
  }

  openPreview(row: Ingestion): void {
    if (this.companyId == null || row.document_id == null) return;

    this.previewingId.set(row.document_id);
    this.preview.set(null);
    this.previewError.set(null);

    this.admin.getKbDocumentContent(this.companyId, row.document_id).subscribe({
      next: (r) => this.preview.set(r),
      error: (err) => {
        const code = err?.error?.error ?? 'preview_failed';
        this.previewError.set(
          code === 'document_not_found'
            ? 'That document no longer exists for this company.'
            : `Could not load the document (${code}).`,
        );
      },
    });
  }

  closePreview(): void {
    this.previewingId.set(null);
    this.preview.set(null);
    this.previewError.set(null);
  }

  loadHistory(): void {
    if (this.companyId == null) return;
    this.admin.listIngestions(this.companyId).subscribe({
      next: (r) => this.ingestions.set(r.ingestions),
      error: () => this.error.set('Failed to load ingestion history.'),
    });
    this.admin.listDeletions(this.companyId).subscribe({
      next: (r) => this.deletions.set(r.deletions),
      error: () => this.error.set('Failed to load deletion history.'),
    });
  }

  isRemoved(row: Ingestion): boolean {
    return row.document_id != null && this.removedDocIds().has(row.document_id);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || this.companyId == null) return;

    this.error.set(null);
    this.result.set(`Ingesting ${file.name}…`);
    this.busy.set(true);
    this.admin.ingest(this.companyId, file).subscribe({
      next: (r) => {
        this.busy.set(false);
        this.result.set(
          `Ingested “${r.filename}”: ${r.chunks_indexed} chunk(s) added to the KB` +
            (r.chunks_blocked ? `, ${r.chunks_blocked} blocked` : '') +
            '.',
        );
        this.loadHistory();
      },
      error: (err) => {
        this.busy.set(false);
        const code = err?.error?.error ?? 'ingest_failed';
        this.result.set(null);
        this.error.set(
          code === 'nothing_to_ingest'
            ? 'Nothing to ingest — every chunk was blocked by the safety gate.'
            : `Ingest failed (${code}).`,
        );
      },
    });
    input.value = '';
  }

  remove(row: Ingestion): void {
    if (this.companyId == null || row.document_id == null || this.isRemoved(row)) return;

    const ok = confirm(
      `Remove “${row.filename}” from this company's knowledge base?\n\n` +
        `Its content will stop being retrievable for every user at the company. ` +
        `The removal is logged.`,
    );
    if (!ok) return;

    this.error.set(null);
    this.removingId.set(row.id);
    this.admin.deleteFromKb(this.companyId, row.document_id).subscribe({
      next: (r) => {
        this.removingId.set(null);
        this.result.set(
          `Removed “${r.filename}” from the KB: ${r.chunks_deleted} chunk(s) deleted.`,
        );
        this.closePreview();
        this.loadHistory();
      },
      error: (err) => {
        this.removingId.set(null);
        const code = err?.error?.error ?? 'delete_failed';
        this.result.set(null);
        this.error.set(
          code === 'document_not_found'
            ? 'That document no longer exists for this company.'
            : `Remove failed (${code}).`,
        );
      },
    });
  }
}
