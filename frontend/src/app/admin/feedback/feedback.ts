import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { FeedbackRow, FeedbackSummary } from '../../core/models';
import { LanguageService } from '../../core/language';
import { AdminService } from '../admin-service';

@Component({
  selector: 'app-feedback-admin',
  imports: [FormsModule, DecimalPipe],
  templateUrl: './feedback.html',
  styleUrl: './feedback.css',
})
export class FeedbackAdmin implements OnInit {
  private admin = inject(AdminService);
  readonly lang = inject(LanguageService);

  readonly summary = signal<FeedbackSummary | null>(null);
  readonly error = signal<string | null>(null);

  sinceDays: number | null = null;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    const days = this.sinceDays;
    const since = days != null && days > 0 ? String(Math.floor(days)) : undefined;
    this.admin.getFeedback({ since }).subscribe({
      next: (s) => {
        this.summary.set(s);
        this.error.set(null);
      },
      error: () => this.error.set('Failed to load feedback.'),
    });
  }

  upPercent(row: FeedbackRow): number {
    return row.rated > 0 ? Math.round((row.up / row.rated) * 100) : 0;
  }

  scoreClass(score: number | null): string {
    if (score == null) return 'none';
    if (score >= 70) return 'good';
    if (score >= 40) return 'mid';
    return 'bad';
  }

  scoreLabel(score: number | null): string {
    return score == null ? '—' : `${score}%`;
  }

  readonly overallScore = computed(() => this.summary()?.total.score ?? null);

  readonly coverage = computed(() => {
    const t = this.summary()?.total;
    return t && t.answers > 0 ? Math.round((t.rated / t.answers) * 100) : 0;
  });

  when(iso: string | null): string {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${pad(d.getDate())}/${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
}
