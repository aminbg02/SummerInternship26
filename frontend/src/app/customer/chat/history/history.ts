import { Component, ElementRef, inject, input, output, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ConversationSummary } from '../../../core/models';
import { LanguageService } from '../../../core/language';

export interface RenameEvent {
  id: number;
  title: string;
}

@Component({
  selector: 'app-chat-history',
  imports: [FormsModule],
  templateUrl: './history.html',
  styleUrl: './history.css',
})
export class ChatHistory {
  readonly lang = inject(LanguageService);

  readonly conversations = input.required<ConversationSummary[]>();
  readonly activeId = input<number | null>(null);

  readonly newChat = output<void>();
  readonly open = output<number>();
  readonly rename = output<RenameEvent>();
  readonly remove = output<number>();

  readonly editingId = signal<number | null>(null);
  private readonly renameBox = viewChild<ElementRef<HTMLInputElement>>('renameBox');
  editDraft = '';

  startRename(c: ConversationSummary, event: Event): void {
    event.stopPropagation();
    this.editDraft = c.title;
    this.editingId.set(c.id);
    setTimeout(() => this.renameBox()?.nativeElement.select());
  }

  commitRename(c: ConversationSummary): void {
    if (this.editingId() !== c.id) return;
    const title = this.editDraft.trim();
    this.editingId.set(null);
    if (!title || title === c.title) return;
    this.rename.emit({ id: c.id, title });
  }

  cancelRename(): void {
    this.editingId.set(null);
  }

  onDelete(id: number, event: Event): void {
    event.stopPropagation();
    this.remove.emit(id);
  }
}
