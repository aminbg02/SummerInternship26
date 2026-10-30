import { Component, inject, signal } from '@angular/core';

import { AdminService } from '../../admin/admin-service';
import { LanguageService } from '../../core/language';

@Component({
  selector: 'app-company-kb',
  templateUrl: './kb.html',
  styleUrl: './kb.css',
})
export class CompanyKb {
  private admin = inject(AdminService);
  readonly lang = inject(LanguageService);

  readonly result = signal<string | null>(null);
  readonly error = signal<string | null>(null);
  readonly busy = signal(false);

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    this.error.set(null);
    this.result.set(`Ingesting ${file.name}…`);
    this.busy.set(true);
    this.admin.ingestOwn(file).subscribe({
      next: (r) => {
        this.busy.set(false);
        this.result.set(
          `Ingested “${r.filename}”: ${r.chunks_indexed} chunk(s) added to your ` +
            `knowledge base` +
            (r.chunks_blocked ? `, ${r.chunks_blocked} blocked by the safety gate` : '') +
            '.',
        );
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
}
