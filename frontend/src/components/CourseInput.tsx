import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { CompletedCourse, CourseHit, Origin } from "../types";

const GRADES = ["", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F", "P"];
const ORIGINS: { value: Origin; label: string }[] = [
  { value: "unc", label: "UNC" },
  { value: "exam", label: "AP/IB/exam" },
  { value: "transfer", label: "Transfer" },
];

interface Props {
  year: string;
  courses: CompletedCourse[];
  onChange: (courses: CompletedCourse[]) => void;
}

export function CourseInput({ year, courses, onChange }: Props) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<CourseHit[]>([]);
  const [active, setActive] = useState(0);
  const timer = useRef<number>();

  useEffect(() => {
    window.clearTimeout(timer.current);
    if (query.trim().length < 2) { setHits([]); return; }
    timer.current = window.setTimeout(() => {
      api.searchCourses(query, year).then((r) => { setHits(r.results); setActive(0); }).catch(() => setHits([]));
    }, 150);
    return () => window.clearTimeout(timer.current);
  }, [query, year]);

  const add = (hit: CourseHit) => {
    if (!courses.some((c) => c.code === hit.code)) {
      onChange([...courses, { code: hit.code, title: hit.title, grade: null, origin: "unc", in_progress: false }]);
    }
    setQuery("");
    setHits([]);
  };
  const update = (code: string, patch: Partial<CompletedCourse>) =>
    onChange(courses.map((c) => (c.code === code ? { ...c, ...patch } : c)));

  return (
    <div className="course-input">
      <div className="combo">
        <input
          type="search"
          value={query}
          placeholder="Search courses, e.g. MATH 231 or Calculus"
          aria-label="Search for a completed course"
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, hits.length - 1)); }
            if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
            if (e.key === "Enter" && hits[active]) { e.preventDefault(); add(hits[active]); }
            if (e.key === "Escape") setHits([]);
          }}
        />
        {hits.length > 0 && (
          <ul className="combo-list" role="listbox">
            {hits.map((h, i) => (
              <li key={h.code} role="option" aria-selected={i === active}
                  className={i === active ? "active" : ""}
                  onMouseDown={(e) => { e.preventDefault(); add(h); }}>
                <b>{h.code}</b> <span>{h.title}</span>
                <em>{h.credits_min === h.credits_max ? h.credits_min : `${h.credits_min}–${h.credits_max}`} cr</em>
              </li>
            ))}
          </ul>
        )}
      </div>
      {courses.length === 0 ? (
        <p className="hint">No courses added. Add AP/IB credit, transfer credit, and courses you are taking now.</p>
      ) : (
        <table className="completed">
          <thead>
            <tr><th>Course</th><th>Grade</th><th>Source</th><th title="Currently enrolled">Now</th><th></th></tr>
          </thead>
          <tbody>
            {courses.map((c) => (
              <tr key={c.code}>
                <td><b>{c.code}</b>{c.title && <small>{c.title}</small>}</td>
                <td>
                  <select value={c.grade ?? ""} aria-label={`Grade for ${c.code}`}
                          disabled={c.in_progress}
                          onChange={(e) => update(c.code, { grade: e.target.value || null })}>
                    {GRADES.map((g) => <option key={g} value={g}>{g || "—"}</option>)}
                  </select>
                </td>
                <td>
                  <select value={c.origin} aria-label={`Source of ${c.code}`}
                          onChange={(e) => update(c.code, { origin: e.target.value as Origin })}>
                    {ORIGINS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </td>
                <td>
                  <input type="checkbox" checked={c.in_progress} aria-label={`${c.code} in progress`}
                         onChange={(e) => update(c.code, { in_progress: e.target.checked, grade: e.target.checked ? null : c.grade })} />
                </td>
                <td>
                  <button className="icon" aria-label={`Remove ${c.code}`}
                          onClick={() => onChange(courses.filter((x) => x.code !== c.code))}>×</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
