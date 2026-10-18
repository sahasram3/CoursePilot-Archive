import { useEffect, useState } from "react";
import { api } from "../api";
import type { CourseDetail } from "../types";

export function CourseDrawer({ code, year, onClose }: { code: string; year: string; onClose: () => void }) {
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCourse(null);
    setError(null);
    api.course(code, year).then(setCourse).catch((e: Error) => setError(e.message));
  }, [code, year]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-label={`${code} details`} onClick={(e) => e.stopPropagation()}>
        <button className="icon close" onClick={onClose} aria-label="Close">×</button>
        {error && <p className="error">{error}</p>}
        {!course && !error && <p>Loading…</p>}
        {course && (
          <>
            <h2>{course.code}</h2>
            <h3>{course.title}</h3>
            <p className="meta">
              {course.credits_min === course.credits_max ? course.credits_min : `${course.credits_min}–${course.credits_max}`} credits
              {course.gen_ed.length > 0 && <> · IDEAs: {course.gen_ed.join(", ")}</>}
              {course.same_as.length > 0 && <> · Same as {course.same_as.join(", ")}</>}
            </p>
            <p>{course.description}</p>
            <h4>Requisites</h4>
            {course.requisites_raw ? (
              <>
                <blockquote>“{course.requisites_raw}”</blockquote>
                <p><b>Interpreted as:</b> {course.prerequisites_text}
                  {course.corequisites_text && <> · <b>Corequisite:</b> {course.corequisites_text}</>}</p>
                <p className={`badge ${course.requisites_status}`}>{statusLabel(course.requisites_status)}</p>
                {course.requisites_notes.map((n) => <p key={n} className="note">{n}</p>)}
              </>
            ) : <p>None listed.</p>}
            <a href={course.source.url} target="_blank" rel="noreferrer">{course.source.catalog_year} catalog ↗</a>
          </>
        )}
      </aside>
    </div>
  );
}

function statusLabel(s: string) {
  return ({
    verified: "Interpretation verified against catalog text",
    parsed: "Parsed automatically (not hand-reviewed)",
    partial: "Partly interpreted — review the catalog text",
    unparsed: "Not interpreted — review the catalog text",
    needs_reverification: "Catalog text changed since review",
    none: "No requisites",
  } as Record<string, string>)[s] ?? s;
}
