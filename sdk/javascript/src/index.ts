export { ObserveML, promptHash } from "./tracker";
export type { TrackOptions } from "./tracker";

// ---------- Module-level convenience API ----------
import { ObserveML } from "./tracker";
import type { TrackOptions } from "./tracker";

let _default: ObserveML | null = null;

export function configure(apiKey: string, endpoint?: string): void {
  _default = new ObserveML(apiKey, endpoint);
}

export function track(options: TrackOptions): void {
  if (!_default) {
    throw new Error(
      "ObserveML not configured. Call configure(apiKey) first."
    );
  }
  _default.track(options);
}
