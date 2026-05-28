import { ExecutionStreamService } from './execution-stream.service';

describe('ExecutionStreamService', () => {
  it('parses SSE data blocks', () => {
    const svc = new ExecutionStreamService('');
    const block =
      'event: trace_event\ndata: {"event_type":"trace_event","execution_id":"e1","sequence":1,"emitted_at":"t","payload":{}}';
    const ev = (svc as unknown as { parseSseBlock(b: string): unknown }).parseSseBlock(block);
    expect(ev).toEqual(
      jasmine.objectContaining({ event_type: 'trace_event', sequence: 1 }),
    );
  });

  it('ignores heartbeat comments', () => {
    const svc = new ExecutionStreamService('');
    const ev = (svc as unknown as { parseSseBlock(b: string): unknown }).parseSseBlock(': heartbeat');
    expect(ev).toBeNull();
  });
});
