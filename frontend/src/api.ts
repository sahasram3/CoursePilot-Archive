import type { CourseDetail, CourseHit, Placement, PlanRequest, PlanResponse, ProgramListing } from "./types";

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = (body as { detail?: unknown }).detail;
    const message = typeof detail === "string" ? detail
      : Array.isArray(detail) ? detail.map((d: { msg?: string }) => d.msg).join("; ")
      : `Request failed (${response.status})`;
    throw new Error(message);
  }
  return body as T;
}

export const api = {
  programs: (year: string) =>
    getJson<{ programs: ProgramListing[]; counts: { discovered: number; plannable: number } }>(
      `/api/programs?catalog_year=${encodeURIComponent(year)}`),
  placements: (programId: string, year: string) =>
    getJson<{ placements: Placement[] }>(
      `/api/programs/${encodeURIComponent(programId)}/placements?catalog_year=${encodeURIComponent(year)}`),
  searchCourses: (q: string, year: string) =>
    getJson<{ results: CourseHit[] }>(
      `/api/courses/search?q=${encodeURIComponent(q)}&catalog_year=${encodeURIComponent(year)}`),
  course: (code: string, year: string) =>
    getJson<CourseDetail>(`/api/courses/${encodeURIComponent(code)}?catalog_year=${encodeURIComponent(year)}`),
  plan: (request: PlanRequest) =>
    getJson<PlanResponse>("/api/plan", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request),
    }),
};
