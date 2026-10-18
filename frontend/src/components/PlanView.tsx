import { useState } from "react";
import type { Issue, Plan, PlanResponse, PlannedCourse, RequirementStatus } from "../types";
import { PrereqMap } from "./PrereqMap";

type Tab = "semesters" | "map" | "requirements" | "checks";

interface Props {
  response: PlanResponse;
  onLock: (code: string, term: string) => void;
  onAvoid: (code: string) => void;
  onShowCourse: (code: string) => void;
  locked: Set<string>;
  busy: boolean;
}

export function PlanView({ response, onLock, onAvoid, onShowCourse, locked, busy }: Props) {
  const [index, setIndex] = useState(0);
  const [tab, setTab] = useState<Tab>("semesters");
  const plan = response.plans[Math.min(index, response.plans.length - 1)];
  const warnings = response.issues.filter((i) => i.severity !== "info").length;
  const uncertain = countStatus(Object.values(plan.requirements).flat(), "uncertain");

  return (
    <div className={`results ${busy ? "stale" : ""}`}>
      <div className="result-head">
        <div>
          <span className="eyebrow">{response.programs.map((p) => p.name).join(" + ")}</span>
          <h2 className="result-title">Graduate {plan.summary.graduation_term}</h2>
        </div>
        <div className="result-actions">
          {response.plans.length > 1 && (
            <div className="seg" role="tablist" aria-label="Alternative plans">
              {response.plans.map((_, i) => (
                <button key={i} role="tab" aria-selected={i === index} className={i === index ? "on" : ""}
                        onClick={() => setIndex(i)}>Option {i + 1}</button>
              ))}
            </div>
          )}
          <button className="ghost-btn" onClick={() => downloadCsv(response, plan)}>Export CSV</button>
          <button className="ghost-btn" onClick={() => window.print()}>Print</button>
        </div>
      </div>

      <div className="banner provisional" role="note">
        <b>Provisional plan, not graduation-certified.</b> Built from the published {response.catalog_year} catalog;
        confirm with your advisor and Tar Heel Tracker.
      </div>

      <Summary plan={plan} />
      <StartingCredit response={response} />

      <div className="tabs" role="tablist" aria-label="Plan views">
        <TabButton id="semesters" tab={tab} setTab={setTab}>Semesters</TabButton>
        <TabButton id="map" tab={tab} setTab={setTab}>Prerequisite map</TabButton>
        <TabButton id="requirements" tab={tab} setTab={setTab}>
          Requirements {uncertain > 0 && <span className="pill warn">{uncertain} uncertain</span>}
        </TabButton>
        <TabButton id="checks" tab={tab} setTab={setTab}>
          Checks {warnings > 0 && <span className="pill">{warnings}</span>}
        </TabButton>
      </div>

      {tab === "semesters" && (
        <div className="terms">
          {plan.terms.map((t) => (
            <article key={t.term} className={`term ${t.term.startsWith("Summer") ? "summer" : ""}`}>
              <header>
                <h3>{t.term}</h3>
                <span className="credits">{t.total_credits} cr</span>
              </header>
              <div className="loadbar" aria-hidden>
                <span style={{ width: `${Math.min(100, (t.course_credits / Math.max(t.total_credits, 1)) * 100)}%` }} />
              </div>
              <ul>
                {t.courses.map((c) => (
                  <CourseRow key={c.code} course={c} term={t.term} locked={locked.has(c.code)}
                             onLock={onLock} onAvoid={onAvoid} onShow={onShowCourse} />
                ))}
                {t.unassigned_credits > 0 && (
                  <li className="placeholder">
                    <span className="code">Gen Ed / elective</span>
                    <span className="cr">{t.unassigned_credits}</span>
                    <small>Open hours for IDEAs in Action courses you choose with your advisor</small>
                  </li>
                )}
              </ul>
            </article>
          ))}
        </div>
      )}
      {tab === "map" && <PrereqMap response={response} plan={plan} onShow={onShowCourse} />}
      {tab === "requirements" && (
        <section className="panel">
          {response.programs.map((p) => (
            <div key={p.id}>
              <h3 className="program-name">
                {p.name} <VerificationBadge status={p.verification.status} />
                <a href={p.url} target="_blank" rel="noreferrer" className="src">catalog page ↗</a>
              </h3>
              <Legend />
              <ul className="tree">
                {plan.requirements[p.id].map((n) => <RequirementNode key={n.id} node={n} onShow={onShowCourse} top />)}
              </ul>
            </div>
          ))}
        </section>
      )}
      {tab === "checks" && (
        <section className="panel">
          <Issues issues={response.issues} />
          <h3 className="small-head">Not modeled yet</h3>
          <ul className="not-modeled">{response.not_modeled.map((x) => <li key={x}>{x}</li>)}</ul>
          <p className="solver">Optimized by {response.solver.engine} in {response.solver.seconds}s
            ({response.solver.statuses.join(", ")}).</p>
        </section>
      )}
    </div>
  );
}

function TabButton({ id, tab, setTab, children }: { id: Tab; tab: Tab; setTab: (t: Tab) => void; children: React.ReactNode }) {
  return (
    <button role="tab" aria-selected={tab === id} className={tab === id ? "tab on" : "tab"} onClick={() => setTab(id)}>
      {children}
    </button>
  );
}

function countStatus(nodes: RequirementStatus[], status: string): number {
  return nodes.reduce((n, node) => n + (node.status === status && node.children.length === 0 ? 1 : 0)
    + countStatus(node.children, status), 0);
}

function Summary({ plan }: { plan: Plan }) {
  const s = plan.summary;
  const pct = Math.min(100, Math.round((s.completed_hours / 120) * 100));
  const capNote = s.ba_subject_cap_applies && s.countable_hours_after_ba_cap !== s.projected_total_hours
    ? `${s.countable_hours_after_ba_cap} count (B.A. 45-hr subject cap)` : "120 required";
  const stats = [
    { label: "Projected hours", value: s.projected_total_hours, note: capNote },
    { label: "Major courses to take", value: s.planned_course_hours, note: "credit hours scheduled" },
    { label: "Gen Ed / elective hours", value: s.unassigned_gen_ed_elective_hours, note: "open slots you choose" },
    { label: "Semesters at UNC", value: s.regular_semesters_entry_to_graduation, note: "Fall/Spring from entry · 8 expected" },
  ];
  return (
    <div className="summary">
      <div className="progress" aria-label={`${s.completed_hours} of 120 hours already earned`}>
        <div className="progress-label"><b>{s.completed_hours}</b> of 120 hours already earned</div>
        <div className="progress-track"><span style={{ width: `${pct}%` }} /></div>
      </div>
      <div className="stats">
        {stats.map((x) => (
          <div key={x.label} className="stat">
            <span className="value">{x.value}</span>
            <span className="label">{x.label}</span>
            <small>{x.note}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

function StartingCredit({ response }: { response: PlanResponse }) {
  const items = response.completed_courses.filter((c) => c.credits > 0 || c.code);
  if (items.length === 0) return null;
  return (
    <div className="starting">
      <span className="label">Starting credit</span>
      <ul>
        {items.map((c, i) => (
          <li key={i} title={c.title} className={c.credits ? "" : "placement"}>
            <b>{c.code ?? c.title}</b>
            <small>{[c.in_progress ? "in progress" : c.grade, c.source !== "UNC" ? c.source : null, c.credits ? `${c.credits} cr` : "placement"]
              .filter(Boolean).join(" · ")}</small>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CourseRow({ course, term, locked, onLock, onAvoid, onShow }: {
  course: PlannedCourse; term: string; locked: boolean;
  onLock: (c: string, t: string) => void; onAvoid: (c: string) => void; onShow: (c: string) => void;
}) {
  const flagged = course.warnings.length + course.contingencies.length;
  const unverified = course.requisites_status === "partial" || course.requisites_status === "unparsed";
  return (
    <li className={`course ${locked ? "locked" : ""}`}>
      <button className="code link" onClick={() => onShow(course.code)} title="Course details">{course.code}</button>
      <span className="cr">{course.credits}</span>
      <span className="title">{course.title}</span>
      <span className="why">{course.reasons.join(" · ")}</span>
      {course.satisfied_by.length > 0 && (
        <span className="needs">Prereqs met by {course.satisfied_by.map((s) => s.replace("PLACEMENT:", "placement → ")).join(", ")}</span>
      )}
      {(flagged > 0 || unverified) && (
        <details className="flags">
          <summary>
            {course.contingencies.length > 0 && <span className="tag amber">grade needed</span>}
            {course.warnings.length > 0 && <span className="tag yellow">{course.warnings.length} note{course.warnings.length > 1 ? "s" : ""}</span>}
          </summary>
          <ul>
            {course.contingencies.map((x) => <li key={x} className="contingency">{x}</li>)}
            {course.warnings.map((x) => <li key={x}>{x}</li>)}
          </ul>
        </details>
      )}
      <span className="actions">
        <button className="mini" title="Keep this course in this term and re-plan" onClick={() => onLock(course.code, term)}
                aria-pressed={locked}>{locked ? "📌 Pinned" : "📌 Pin here"}</button>
        <button className="mini" title="Re-plan without this course" onClick={() => onAvoid(course.code)}>Avoid</button>
      </span>
    </li>
  );
}

const STATUS_LABEL: Record<RequirementStatus["status"], string> = {
  completed: "Done", planned: "Planned", uncertain: "Uncertain", unmet: "Not met", not_needed: "Alternative",
};

function Legend() {
  return (
    <p className="legend">
      <span><i className="dot completed" /> Done</span>
      <span><i className="dot planned" /> Planned</span>
      <span><i className="dot uncertain" /> Uncertain (never counted as met)</span>
      <span><i className="dot not_needed" /> Unused alternative</span>
    </p>
  );
}

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
        <button className="mini ghost" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? "hide source" : "source"}</button>
      </div>
      {open && (
        <div className="provenance">
          <VerificationBadge status={node.verification.status} />
          {node.verification.on && <span className="muted"> reviewed {node.verification.on}</span>}
          {node.source.text && (
            <blockquote>
              {node.source.text.split("||").map((part) => (
                <p key={part}>“{part.replace(/\s*\|\s*/g, " · ").trim()}”</p>
              ))}
            </blockquote>
          )}
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
    needs_reverification: "Catalog changed: re-review", partial: "Partly interpreted", unparsed: "Not interpreted",
  };
  return <span className={`badge ${status}`}>{label[status] ?? status}</span>;
}

export function Issues({ issues }: { issues: Issue[] }) {
  const order = { blocker: 0, warning: 1, info: 2 };
  if (issues.length === 0) return <p className="muted">No issues found.</p>;
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

function downloadCsv(response: PlanResponse, plan: Plan) {
  const rows = [["Term", "Course", "Title", "Credits", "Why"]];
  for (const t of plan.terms) {
    for (const c of t.courses) rows.push([t.term, c.code, c.title, String(c.credits), c.reasons.join("; ")]);
    if (t.unassigned_credits) rows.push([t.term, "", "Gen Ed / elective (open)", String(t.unassigned_credits), ""]);
  }
  rows.push([], ["Provisional plan, not graduation-certified.", `Catalog ${response.catalog_year}`]);
  const csv = rows.map((r) => r.map((v) => `"${(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "coursepilot-plan.csv";
  a.click();
  URL.revokeObjectURL(url);
}
