// Mirrors backend/prereqpath/terms.py.
const SEASONS = ["Spring", "Summer", "Fall"] as const;

export function termKey(label: string): number {
  const [season, year] = label.split(" ");
  return Number(year) * 3 + SEASONS.indexOf(season as (typeof SEASONS)[number]);
}

export function regularTerms(from: string, to: string): string[] {
  const out: string[] = [];
  for (let k = termKey(from); k <= termKey(to); k++) {
    const season = SEASONS[k % 3];
    if (season !== "Summer") out.push(`${season} ${Math.floor(k / 3)}`);
  }
  return out;
}

/** The next Fall/Spring term after today (registration-relevant planning start). */
export function nextRegularTerm(today = new Date()): string {
  const year = today.getFullYear();
  // Spring classes start in January; Fall in August.
  return today.getMonth() >= 7 ? `Spring ${year + 1}` : `Fall ${year}`;
}

export function addRegularTerms(label: string, count: number): string {
  let k = termKey(label);
  let added = 0;
  while (added < count) {
    k++;
    if (SEASONS[k % 3] !== "Summer") added++;
  }
  return `${SEASONS[k % 3]} ${Math.floor(k / 3)}`;
}
