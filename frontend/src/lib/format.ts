const MINUS = "−";

export function signed(value: number, digits = 2): string {
  const fixed = Math.abs(value).toFixed(digits);
  if (Number(fixed) === 0) return fixed;
  return `${value < 0 ? MINUS : "+"}${fixed}`;
}

export function usdMillions(value: number, digits = 1, showPlus = false): string {
  const amount = (Math.abs(value) / 1e6).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  const sign = value < 0 ? MINUS : showPlus && value > 0 ? "+" : "";
  return `${sign}$${amount}m`;
}

export function percent(value: number, digits = 2, showPlus = true): string {
  const amount = (Math.abs(value) * 100).toFixed(digits);
  const sign = value < 0 ? MINUS : showPlus && value > 0 ? "+" : "";
  return `${sign}${amount}%`;
}

export function basisPoints(value: number): string {
  return `${signed(value, 0)} bp`;
}

export function integer(value: number): string {
  return value.toLocaleString("en-US");
}

export function score(value: number, digits = 1): string {
  return value.toFixed(digits);
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export const TIME_ZONE_LABEL = "IST";
const IST_OFFSET_MS = 330 * 60 * 1000;

function parts(iso: string) {
  const date = iso.length === 10 ? new Date(`${iso}T00:00:00Z`) : new Date(Date.parse(iso) + IST_OFFSET_MS);
  return {
    day: String(date.getUTCDate()).padStart(2, "0"),
    month: MONTHS[date.getUTCMonth()],
    year: date.getUTCFullYear(),
    time: `${String(date.getUTCHours()).padStart(2, "0")}:${String(date.getUTCMinutes()).padStart(2, "0")}`,
    weekday: WEEKDAYS[date.getUTCDay()],
  };
}

export function day(iso: string): string {
  const p = parts(iso);
  return `${p.day} ${p.month} ${p.year}`;
}

export function shortDay(iso: string): string {
  const p = parts(iso);
  return `${p.day} ${p.month}`;
}

export function dayWithWeekday(iso: string): string {
  const p = parts(iso);
  return `${p.weekday} ${p.day} ${p.month} ${p.year}`;
}

export function dateTime(iso: string): string {
  const p = parts(iso);
  return `${p.day} ${p.month} ${p.year}, ${p.time} ${TIME_ZONE_LABEL}`;
}

export function time(iso: string): string {
  return parts(iso).time;
}

export function humanize(value: string): string {
  const text = value.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function safeHttpUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}
