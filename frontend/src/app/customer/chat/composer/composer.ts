import { Component, inject, input, model, output } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { LanguageService } from '../../../core/language';

@Component({
  selector: 'app-chat-composer',
  imports: [FormsModule],
  templateUrl: './composer.html',
  styleUrl: './composer.css',
})
export class ChatComposer {
  readonly lang = inject(LanguageService);

  readonly draft = model<string>('');
  readonly canSend = input<boolean>(false);

  readonly send = output<void>();
  readonly fileSelected = output<File>();

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) this.fileSelected.emit(file);
    input.value = '';
  }
}
