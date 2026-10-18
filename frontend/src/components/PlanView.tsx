import { useState } from "react";
import type { Issue, Plan, PlanResponse, PlannedCourse, RequirementStatus } from "../types";

interface Props {
  response: PlanResponse;
  onLock: (code: string, term: string) => void;
  onAvoid: (code: string) => void;
  onShowCourse: (code: string) => void;
  locked: Set<string>;
}

export function PlanView({ response, onLock, onAvoid, onShowCourse, locked }: Props) {
  const [index, setIndex] = useState(0);
  const plan = response.plans[Math.min(index, response.plans.length - 1)];
  return (
    <div className="results">
      <div className="banner provisional" role="note">
        <b>Provisional plan — not graduation-certified.</b> {response.certification_note}
      </div>
      {response.plans.length > 1 && (
        <div className="tabs" role="tablist">
          {response.plans.map((_, i) => (
            <button key={i} role="tab" aria-selected={i === index} className={i === index ? "tab on" : "tab"}
                    onClick={() => setIndex(i)}>Option {i + 1}</button>
          ))}
        </div>
      )}
      <Summary plan={plan} />
      <div className="terms">
        {plan.terms.map((t) => (
          <article key={t.term} className={`term ${t.term.startsWith("Summer") ? "summer" : ""}`}>
            <header>
              <h3>{t.term}</h3>
              <span className="credits">{t.total_credits} cr</span>
            </header>
            <ul>
              {t.courses.map((c) => (
                <CourseRow key={c.code} course={c} term={t.term} locked={locked.has(c.code)}
                           onLock={onLock} onAvoid={onAvoid} onShow={onShowCourse} />
              ))}
              {t.unassigned_credits > 0 && (
                <li className="placeholder">
                  <span className="code">Gen Ed / elective</span>
                  <span className="cr">{t.unassigned_credits}</span>
                  <small>Unassigned hours: choose IDEAs in Action courses with your advisor</small>
                </li>
              )}
            </ul>
          </article>
        ))}
      </div>
      <div className="two-col">
        <section className="panel">
          <h2>Requirements</h2>
          {response.programs.map((p) => (
            <div key={p.id}>
              <h3 className="program-name">
                {p.name} <VerificationBadge status={p.verification.status} />
                <a href={p.url} target="_blank" rel="noreferrer" className="src">catalog ↗</a>
              </h3>
              <ul className="tree">
                {plan.requirements[p.id].map((n) => <RequirementNode key={n.id} node={n} onShow={onShowCourse} top />)}
              </ul>
            </div>
          ))}
        </section>
        <section className="panel">
          <h2>Notes &amp; checks</h2>
          <Issues issues={response.issues} />
          <h3 className="small-head">Not modeled yet</h3>
          <ul className="not-modeled">{response.not_modeled.map((x) => <li key={x}>{x}</li>)}</ul>
          <p className="solver">Solved by {response.solver.engine} in {response.solver.seconds}s.</p>
        </section>
      </div>
    </div>
  );
}

function Summary({ plan }: { plan: Plan }) {
  const s = plan.summary;
  const stats = [
    { label: "Projected hours", value: s.projected_total_hours, note: s.ba_subject_cap_applies && s.countable_hours_after_ba_cap !== s.projected_total_hours ? `${s.countable_hours_after_ba_cap} count toward 120` : "120 required" },
    { label: "Program courses planned", value: s.planned_course_hours, note: "hours" },
    { label: "Gen Ed / elective slots", value: s.unassigned_gen_ed_elective_hours, note: "hours to choose" },
    { label: "Fall/Spring semesters", value: s.regular_semesters_entry_to_graduation, note: "from entry; 8 expected" },
  ];
  return (
    <div className="stats">
      {stats.map((x) => (
        <div key={x.label} className="stat">
          <span className="value">{x.value}</span>
          <span className="label">{x.label}</span>
          <small>{x.note}</small>
        </div>
      ))}
    </div>
  );
}

function CourseRow({ course, term, locked, onLock, onAvoid, onShow }: {
  course: PlannedCourse; term: string; locked: boolean;
  onLock: (c: string, t: string) => void; onAvoid: (c: string) => void; onShow: (c: string) => void;
}) {
  const flagged = course.warnings.length + course.contingencies.length;
  return (
    <li className={`course ${locked ? "locked" : ""}`}>
      <button className="code link" onClick={() => onShow(course.code)}>{course.code}</button>
      <span className="cr">{course.credits}</span>
      <span className="title">{course.title}</span>
      <span className="why">{course.reasons.join(" · ")}</span>
      {flagged > 0 && (
        <details className="flags">
          <summary>{course.contingencies.length > 0 && <span className="tag amber">grade needed</span>}
            {course.warnings.length > 0 && <span className="tag yellow">{course.warnings.length} note{course.warnings.length > 1 ? "s" : ""}</span>}</summary>
          <ul>
            {course.contingencies.map((x) => <li key={x} className="contingency">{x}</li>)}
            {course.warnings.map((x) => <li key={x}>{x}</li>)}
          </ul>
        </details>
      )}
      <span className="actions">
        <button className="mini" title="Keep this course in this term" onClick={() => onLock(course.code, term)}
                aria-pressed={locked}>{locked ? "📌 Kept" : "📌 Keep here"}</button>
        <button className="mini" title="Plan without this course" onClick={() => onAvoid(course.code)}>Avoid</button>
      </span>
    </li>
  );
}

const STATUS_LABEL: Record<RequirementStatus["status"], string> = {
  completed: "Done", planned: "Planned", uncertain: "Uncertain", unmet: "Not met", not_needed: "Alternative",
};

function RequirementNode({ node, onShow, top = false }: {
  node: RequirementStatus; onShow: (c: string) => void; top?: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <li className={`req ${node.status}`}>
      <div className="req-line">
        <span className={`dot ${node.status}`} aria-hidden />
        <span className="req-label">{node.label}</span>
        <span className={`status ${node.status}`}>{STATUS_LABEL[node.status]}</span>
        {top && !node.core && (
          <span className="tag" title="Outside the major core: not part of core GPA, residency, or double-counting rules">not core</span>
        )}
        {node.courses.map((c) => (
          <button key={c.code} className="chip link" onClick={() => onShow(c.code)}>
            {c.code}{c.term ? ` · ${c.term}` : " · done"}
          </button>
        ))}
        <button className="mini ghost" onClick={() => setOpen(!open)} aria-expanded={open}>source</button>
      </div>
      {open && (
        <div className="provenance">
          <VerificationBadge status={node.verification.status} />
          {node.verification.on && <span> reviewed {node.verification.on}</span>}
          {node.source.text && <blockquote>“{node.source.text}”</blockquote>}
          {node.verification.notes.map((n) => <p key={n} className="note">{n}</p>)}
          <a href={node.source.url} target="_blank" rel="noreferrer">{node.source.catalog_year} catalog ↗</a>
        </div>
      )}
      {node.children.length > 0 && (
        <ul>{node.children.map((c) => <RequirementNode key={c.id} node={c} onShow={onShow} />)}</ul>
      )}
    </li>
  );
}

export function VerificationBadge({ status }: { status: string }) {
  const label: Record<string, string> = {
    verified: "Verified against catalog", parsed: "Parsed, not reviewed", uncertain: "Uncertain",
    needs_reverification: "Catalog changed — re-review",
  };
  return <span className={`badge ${status}`}>{label[status] ?? status}</span>;
}

export function Issues({ issues }: { issues: Issue[] }) {
  const order = { blocker: 0, warning: 1, info: 2 };
  return (
    <ul className="issues">
      {[...issues].sort((a, b) => order[a.severity] - order[b.severity]).map((i, k) => (
        <li key={k} className={i.severity}>
          <span className="sev">{i.severity}</span> {i.message}
          {i.source_url && <> <a href={i.source_url} target="_blank" rel="noreferrer">source ↗</a></>}
        </li>
      ))}
    </ul>
  );
}
