import { SlicePipe, UpperCasePipe } from '@angular/common';
import { Component, inject, input, output } from '@angular/core';

import { ChatMessage } from '../../../core/models';
import { LanguageService } from '../../../core/language';

@Component({
  selector: 'app-chat-transcript',
  imports: [SlicePipe, UpperCasePipe],
  templateUrl: './transcript.html',
  styleUrl: './transcript.css',
})
export class ChatTranscript {
  readonly lang = inject(LanguageService);

  readonly messages = input<ChatMessage[]>([]);
  readonly loading = input<boolean>(false);
  readonly userEmail = input<string>('');
  readonly feedback = output<{ id: number; value: 'up' | 'down' }>();
}
