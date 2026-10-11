import { useSyncExternalStore } from "react";

export type PageId = "overview" | "signals" | "stress" | "headline";

export const PAGES: PageId[] = ["overview", "signals", "stress", "headline"];

export interface Route {
  page: PageId;
  param: string | null;
}

export function parseHash(hash: string): Route {
  const [rawPage, ...rest] = hash.replace(/^#\/?/, "").split("/");
  const page = (PAGES as string[]).includes(rawPage) ? (rawPage as PageId) : "overview";
  const param = rest.length ? decodeURIComponent(rest.join("/")) : null;
  return { page, param };
}

export function href(page: PageId, param?: string | null): string {
  return param ? `#/${page}/${encodeURIComponent(param)}` : `#/${page}`;
}

export function navigate(page: PageId, param?: string | null): void {
  window.location.hash = href(page, param);
}

function subscribe(callback: () => void): () => void {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}

export function useRoute(): Route {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash, () => "");
  return parseHash(hash);
}
