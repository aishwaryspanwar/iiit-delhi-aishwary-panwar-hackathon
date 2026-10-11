export interface GeoPlace {
  name: string;
  lon: number;
  lat: number;
  iso: string | null;
}

export const GEO_PLACES: Record<string, GeoPlace> = {
  AE: { name: "United Arab Emirates", lon: 54.4, lat: 24.0, iso: "784" },
  AR: { name: "Argentina", lon: -64.0, lat: -34.0, iso: "032" },
  AT: { name: "Austria", lon: 14.5, lat: 47.5, iso: "040" },
  AU: { name: "Australia", lon: 134.0, lat: -25.0, iso: "036" },
  BR: { name: "Brazil", lon: -52.0, lat: -10.0, iso: "076" },
  BY: { name: "Belarus", lon: 28.0, lat: 53.5, iso: "112" },
  CA: { name: "Canada", lon: -100.0, lat: 57.0, iso: "124" },
  CH: { name: "Switzerland", lon: 8.2, lat: 46.8, iso: "756" },
  CN: { name: "China", lon: 104.0, lat: 35.0, iso: "156" },
  DE: { name: "Germany", lon: 10.4, lat: 51.2, iso: "276" },
  EG: { name: "Egypt", lon: 30.0, lat: 26.8, iso: "818" },
  ES: { name: "Spain", lon: -3.7, lat: 40.2, iso: "724" },
  EU: { name: "European Union", lon: -14.0, lat: 47.5, iso: null },
  FI: { name: "Finland", lon: 26.0, lat: 64.0, iso: "246" },
  FR: { name: "France", lon: 2.3, lat: 46.6, iso: "250" },
  GB: { name: "United Kingdom", lon: -1.8, lat: 53.0, iso: "826" },
  GR: { name: "Greece", lon: 22.0, lat: 39.0, iso: "300" },
  HK: { name: "Hong Kong", lon: 114.2, lat: 22.3, iso: null },
  HU: { name: "Hungary", lon: 19.5, lat: 47.2, iso: "348" },
  ID: { name: "Indonesia", lon: 117.0, lat: -2.5, iso: "360" },
  IL: { name: "Israel", lon: 34.9, lat: 31.4, iso: "376" },
  IN: { name: "India", lon: 79.0, lat: 22.0, iso: "356" },
  IQ: { name: "Iraq", lon: 43.7, lat: 33.2, iso: "368" },
  IR: { name: "Iran", lon: 53.7, lat: 32.4, iso: "364" },
  IT: { name: "Italy", lon: 12.6, lat: 42.8, iso: "380" },
  JP: { name: "Japan", lon: 138.3, lat: 36.2, iso: "392" },
  KP: { name: "North Korea", lon: 127.3, lat: 40.2, iso: "408" },
  KR: { name: "South Korea", lon: 127.8, lat: 36.4, iso: "410" },
  KW: { name: "Kuwait", lon: 47.6, lat: 29.3, iso: "414" },
  KZ: { name: "Kazakhstan", lon: 67.0, lat: 48.0, iso: "398" },
  LB: { name: "Lebanon", lon: 35.9, lat: 33.9, iso: "422" },
  LK: { name: "Sri Lanka", lon: 80.7, lat: 7.9, iso: "144" },
  MD: { name: "Moldova", lon: 28.4, lat: 47.4, iso: "498" },
  MX: { name: "Mexico", lon: -102.0, lat: 23.6, iso: "484" },
  NG: { name: "Nigeria", lon: 8.7, lat: 9.1, iso: "566" },
  NL: { name: "Netherlands", lon: 5.3, lat: 52.1, iso: "528" },
  NO: { name: "Norway", lon: 9.0, lat: 61.5, iso: "578" },
  PK: { name: "Pakistan", lon: 69.3, lat: 30.4, iso: "586" },
  PL: { name: "Poland", lon: 19.1, lat: 52.0, iso: "616" },
  PS: { name: "Palestine", lon: 35.2, lat: 31.9, iso: "275" },
  QA: { name: "Qatar", lon: 51.2, lat: 25.3, iso: "634" },
  RU: { name: "Russia", lon: 95.0, lat: 61.0, iso: "643" },
  SA: { name: "Saudi Arabia", lon: 45.0, lat: 24.0, iso: "682" },
  SE: { name: "Sweden", lon: 16.0, lat: 62.0, iso: "752" },
  SG: { name: "Singapore", lon: 103.8, lat: 1.35, iso: null },
  SY: { name: "Syria", lon: 38.5, lat: 35.0, iso: "760" },
  TR: { name: "Turkey", lon: 35.0, lat: 39.0, iso: "792" },
  TW: { name: "Taiwan", lon: 121.0, lat: 23.7, iso: "158" },
  UA: { name: "Ukraine", lon: 31.2, lat: 49.0, iso: "804" },
  US: { name: "United States", lon: -98.5, lat: 39.5, iso: "840" },
  VE: { name: "Venezuela", lon: -66.6, lat: 7.0, iso: "862" },
  VN: { name: "Vietnam", lon: 108.0, lat: 14.5, iso: "704" },
  YE: { name: "Yemen", lon: 48.0, lat: 15.5, iso: "887" },
  ZA: { name: "South Africa", lon: 24.0, lat: -29.0, iso: "710" },
};

export function placeName(code: string): string {
  return GEO_PLACES[code]?.name ?? code;
}
