"""Main-thread UI dispatch for desktop views."""
import queue
import threading

POLL_BATCH = 100


class UiDispatcher:
    """Workers only enqueue Python callbacks; only the main thread calls Tk."""
    def __init__(self, root):
        self.root = root
        self._queue = queue.Queue()
        self._lock = threading.Lock()
        self._closed = False
        self._after_id = root.after(50, self._poll)

    def submit(self, callback):
        with self._lock:
            if not self._closed:
                self._queue.put(callback)

    def _poll(self):
        self._after_id = None
        try:
            for _ in range(POLL_BATCH):
                if self._closed:
                    break
                try:
                    callback = self._queue.get_nowait()
                except queue.Empty:
                    break
                callback()
        finally:
            if not self._closed:
                self._after_id = self.root.after(50, self._poll)

    def close(self):
        """Called on the main thread before its widgets are destroyed."""
        with self._lock:
            self._closed = True
            while True:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None

