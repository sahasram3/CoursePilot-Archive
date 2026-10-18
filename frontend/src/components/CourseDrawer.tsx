import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { CourseDetail } from "../types";
import { VerificationBadge } from "./PlanView";

interface Props {
  code: string;
  year: string;
  planned?: { term: string; satisfiedBy: string[]; reasons: string[] };
  onClose: () => void;
}

export function CourseDrawer({ code, year, planned, onClose }: Props) {
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setCourse(null);
    setError(null);
    api.course(code, year).then(setCourse).catch((e: Error) =>
      setError(code.endsWith("P") ? `${code} is placement credit, not a catalog course.` : e.message));
  }, [code, year]);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={`${code} details`} onClick={(e) => e.stopPropagation()}>
        <button ref={closeRef} className="icon close" onClick={onClose} aria-label="Close">×</button>
        {error && <><h2>{code}</h2><p className="muted">{error}</p></>}
        {!course && !error && <div className="sk-line wide" aria-label="Loading" />}
        {course && (
          <>
            <span className="eyebrow">{course.credits_min === course.credits_max ? course.credits_min : `${course.credits_min}–${course.credits_max}`} credit hours</span>
            <h2>{course.code}</h2>
            <h3>{course.title}</h3>
            {planned && (
              <div className="in-plan">
                <b>In your plan: {planned.term}</b>
                <p>{planned.reasons.join(" · ")}</p>
                {planned.satisfiedBy.length > 0 && <p>Prerequisites met by {planned.satisfiedBy.join(", ")}</p>}
              </div>
            )}
            <div className="meta">
              {course.gen_ed.length > 0 && <span className="tag">IDEAs: {course.gen_ed.join(", ")}</span>}
              {course.same_as.length > 0 && <span className="tag">Same as {course.same_as.join(", ")}</span>}
            </div>
            <p>{course.description}</p>
            <h4>Requisites</h4>
            {course.requisites_raw ? (
              <>
                <blockquote>“{course.requisites_raw}”</blockquote>
                <p><b>Interpreted as:</b> <code>{course.prerequisites_text}</code>
                  {course.corequisites_text && <> · <b>Corequisite:</b> <code>{course.corequisites_text}</code></>}</p>
                <VerificationBadge status={course.requisites_status} />
                {course.requisites_notes.map((n) => <p key={n} className="note">{n}</p>)}
              </>
            ) : <p className="muted">None listed in the catalog.</p>}
            <p><a href={course.source.url} target="_blank" rel="noreferrer">View in the {course.source.catalog_year} catalog ↗</a></p>
          </>
        )}
      </aside>
    </div>
  );
}
