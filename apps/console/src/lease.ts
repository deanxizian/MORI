/** Foreground intent only; reconnect never replays motion or claims control. */
export class LeaseGuard {
  active = false;
  constructor(private stop: () => void) {}
  claim() {
    this.active = true;
  }
  release() {
    this.active = false;
    this.stop();
  }
  heartbeat(visible: boolean, connected: boolean, fresh: boolean) {
    if (!visible || !connected || !fresh) {
      if (this.active) this.release();
      return false;
    }
    return this.active;
  }
}
