import { Inject, Injectable } from '@angular/core';
import { API_BASE_URL } from './api-base-url.token';
import { DEV_AUTH_HEADERS } from './dev-auth-headers';
import type { ExecutionStreamEvent } from '../models/stream.models';

export type StreamEventHandler = (event: ExecutionStreamEvent) => void;
export type StreamErrorHandler = (message: string) => void;

/**
 * SSE client via fetch so dev auth headers are included (EventSource cannot set headers).
 */
@Injectable({ providedIn: 'root' })
export class ExecutionStreamService {
  constructor(@Inject(API_BASE_URL) private readonly baseUrl: string) {}

  connect(
    executionId: string,
    handlers: {
      onEvent: StreamEventHandler;
      onError?: StreamErrorHandler;
      onClose?: () => void;
    },
  ): AbortController {
    const controller = new AbortController();
    const url = `${this.baseUrl.replace(/\/$/, '')}/v1/executions/${executionId}/stream`;

    void this.runStream(url, controller, handlers);
    return controller;
  }

  private async runStream(
    url: string,
    controller: AbortController,
    handlers: {
      onEvent: StreamEventHandler;
      onError?: StreamErrorHandler;
      onClose?: () => void;
    },
  ): Promise<void> {
    try {
      const res = await fetch(url, {
        headers: { Accept: 'text/event-stream', ...DEV_AUTH_HEADERS },
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        handlers.onError?.(`Stream failed (${res.status})`);
        handlers.onClose?.();
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() ?? '';
        for (const block of parts) {
          const ev = this.parseSseBlock(block);
          if (ev) handlers.onEvent(ev);
        }
      }
      handlers.onClose?.();
    } catch (err: unknown) {
      if (controller.signal.aborted) {
        handlers.onClose?.();
        return;
      }
      const msg = err instanceof Error ? err.message : 'Stream error';
      handlers.onError?.(msg);
      handlers.onClose?.();
    }
  }

  private parseSseBlock(block: string): ExecutionStreamEvent | null {
    const trimmed = block.trim();
    if (!trimmed || trimmed.startsWith(':')) return null;
    const dataLine = trimmed.split('\n').find((ln) => ln.startsWith('data: '));
    if (!dataLine) return null;
    try {
      return JSON.parse(dataLine.slice(6)) as ExecutionStreamEvent;
    } catch {
      return null;
    }
  }
}
