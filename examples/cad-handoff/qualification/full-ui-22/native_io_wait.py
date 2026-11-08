"""One waiting poll per request; unchanged original admission/publication/history."""
import sys
import time
from base_native_io import Runner as OriginalRunner, wire


class Runner(OriginalRunner):
    def execute(self, call):
        if call['operation'] != 'poll':
            return super().execute(call)
        while True:
            result = super().execute(call)
            if result['status'] != 'idle':
                return result
            time.sleep(.05)


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2: raise ValueError('Exactly one structured helper argument required')
        response = Runner('/home/cad/ict-mailbox-21', '/work/transport.json').run(sys.argv[1])
    except Exception as exc:
        response = dict(io_protocol='ict-native-io/1',ok=False,entry_error=type(exc).__name__+': '+str(exc))
    sys.stdout.buffer.write(wire(response)); sys.stdout.buffer.flush()
    raise SystemExit(0 if response['ok'] else 1)
