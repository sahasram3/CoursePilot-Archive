import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { CourseDrawer } from "./components/CourseDrawer";
import { FormState, PlanForm } from "./components/PlanForm";
import { Issues, PlanView } from "./components/PlanView";
import { addRegularTerms, nextRegularTerm, termKey } from "./terms";
import type { ExamCatalog, PlanRequest, PlanResponse, ProgramListing } from "./types";

const YEAR = "2026-2027";
const STORAGE_KEY = "prereqpath.form.v2";

function defaultForm(): FormState {
  const entry = "Fall 2026";
  const next = nextRegularTerm();
  return {
    program: "mathematics-major-ba", secondMajor: "", entryTerm: entry,
    firstTerm: termKey(next) < termKey(entry) ? entry : next,
    graduationTerm: addRegularTerms(entry, 7), includeSummer: false, maxCredits: 18,
    targetProgramCredits: 8, completed: [], exams: [], otherCredit: [], tokens: [], locks: [], exclude: [],
    alternatives: 2,
  };
}

function loadForm(): FormState {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return { ...defaultForm(), ...JSON.parse(saved) };
  } catch { /* storage unavailable or corrupt: defaults */ }
  return defaultForm();
}

function toRequest(f: FormState): PlanRequest {
  return {
    catalog_year: YEAR, programs: [f.program, f.secondMajor].filter(Boolean), entry_term: f.entryTerm, first_term: f.firstTerm,
    graduation_term: f.graduationTerm, include_summer: f.includeSummer, min_credits: 12,
    max_credits: f.maxCredits, target_program_credits: f.targetProgramCredits,
    completed: f.completed.map(({ code, grade, origin, in_progress }) => ({ code, grade, origin, in_progress })),
    exams: f.exams, other_credit: f.otherCredit,
    tokens: f.tokens, locks: f.locks, exclude: f.exclude, alternatives: f.alternatives,
  };
}

// Apply a server-suggested fix ({graduation_term, include_summer, locks, max_credits, tokens}) to the form.
function applyChanges(f: FormState, changes: Record<string, unknown>): FormState {
  const next = { ...f };
  if (typeof changes.graduation_term === "string") next.graduationTerm = changes.graduation_term;
  if (typeof changes.include_summer === "boolean") next.includeSummer = changes.include_summer;
  if (typeof changes.max_credits === "number") next.maxCredits = changes.max_credits;
  if (Array.isArray(changes.locks)) next.locks = [];
  if (Array.isArray(changes.tokens)) next.tokens = changes.tokens as string[];
  return next;
}

export default function App() {
  const [programs, setPrograms] = useState<ProgramListing[]>([]);
  const [examCatalog, setExamCatalog] = useState<ExamCatalog | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(loadForm);
  const [response, setResponse] = useState<PlanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [drawer, setDrawer] = useState<string | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const requestId = useRef(0);

  const loadCatalog = useCallback(() => {
    setLoadError(null);
    Promise.all([api.programs(YEAR), api.exams(YEAR)])
      .then(([p, e]) => {
        setPrograms(p.programs);
        setExamCatalog(e);
        // A saved program that is no longer plannable falls back to the first plannable one.
        const plannable = new Set(p.programs.filter((x) => x.plannable).map((x) => x.id));
        setForm((f) => ({
          ...f,
          program: plannable.has(f.program) ? f.program : [...plannable][0] ?? "",
          secondMajor: plannable.has(f.secondMajor) && f.secondMajor !== f.program ? f.secondMajor : "",
        }));
      })
      .catch((e: Error) => setLoadError(e.message || "The planner service is unreachable."));
  }, []);
  useEffect(loadCatalog, [loadCatalog]);
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(form)); } catch { /* ignore */ }
  }, [form]);

  const run = useCallback(async (f: FormState) => {
    const id = ++requestId.current;
    setBusy(true);
    setError(null);
    try {
      const result = await api.plan(toRequest(f));
      if (id !== requestId.current) return;          // a newer request superseded this one
      setResponse(result);
      if (window.matchMedia("(max-width: 960px)").matches) {
        resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (e) {
      if (id !== requestId.current) return;
      setError((e as Error).message || "Planning failed.");
    } finally {
      if (id === requestId.current) setBusy(false);
    }
  }, []);

  const updateAndRun = (patch: Partial<FormState>) => {
    const next = { ...form, ...patch };
    setForm(next);
    run(next);
  };
  const locked = useMemo(() => new Set(form.locks.map((l) => l.code)), [form.locks]);
  const planned = useMemo(() => {
    const map = new Map<string, { term: string; satisfiedBy: string[]; reasons: string[] }>();
    response?.plans[0]?.terms.forEach((t) => t.courses.forEach((c) =>
      map.set(c.code, { term: t.term, satisfiedBy: c.satisfied_by, reasons: c.reasons })));
    return map;
  }, [response]);

  return (
    <div className="app">
      <header className="top">
        <div className="brand"><span className="logo" aria-hidden>C</span> CoursePilot</div>
        <nav className="top-meta">
          <span className="catalog-tag">UNC-Chapel Hill · {YEAR} catalog</span>
        </nav>
      </header>

      {loadError ? (
        <main className="single">
          <div className="panel state-card" role="alert">
            <h2>Can't reach the planner service</h2>
            <p>{loadError}</p>
            <button className="primary" onClick={loadCatalog}>Try again</button>
          </div>
        </main>
      ) : (
        <main>
          <PlanForm year={YEAR} programs={programs} examCatalog={examCatalog} form={form} setForm={setForm}
                    busy={busy} onSubmit={() => run(form)}
                    onReset={() => { setForm(defaultForm()); setResponse(null); setError(null); }} />
          <div className="output" ref={resultsRef} aria-live="polite">
            {error && (
              <div className="banner error" role="alert">
                <b>Couldn't build a plan.</b> {error}
                <button className="ghost-btn" onClick={() => run(form)}>Retry</button>
              </div>
            )}
            {busy && !response && <Skeleton />}
            {!busy && !response && !error && <Hero />}
            {response?.status === "infeasible" && response.infeasibility && (
              <div className={`panel infeasible ${busy ? "stale" : ""}`}>
                <span className="eyebrow">No plan fits these constraints</span>
                <h2>{response.infeasibility.summary}</h2>
                {response.infeasibility.actions.length > 0 && (
                  <>
                    <h3>Fix it in one click</h3>
                    <div className="fixes">
                      {response.infeasibility.actions.map((a) => (
                        <button key={a.label} className="fix" disabled={busy}
                                onClick={() => updateAndRun(applyChanges(form, a.changes))}>{a.label} →</button>
                      ))}
                    </div>
                  </>
                )}
                <h3>Why</h3>
                <ul className="causes">{response.infeasibility.causes.map((c) => <li key={c}>{c}</li>)}</ul>
                <details>
                  <summary>All notes</summary>
                  <Issues issues={response.issues} />
                </details>
              </div>
            )}
            {response?.status === "feasible" && (
              <PlanView
                response={response} locked={locked} busy={busy} onShowCourse={setDrawer}
                onLock={(code, term) => {
                  const exists = form.locks.some((l) => l.code === code);
                  updateAndRun({ locks: exists ? form.locks.filter((l) => l.code !== code) : [...form.locks, { code, term }] });
                }}
                onAvoid={(code) => updateAndRun({
                  exclude: [...new Set([...form.exclude, code])], locks: form.locks.filter((l) => l.code !== code),
                })}
              />
            )}
          </div>
        </main>
      )}
      <footer>
        CoursePilot is an independent student project, not affiliated with or endorsed by UNC-Chapel Hill. Plans are
        provisional and never graduation-certified; confirm with your academic advisor and Tar Heel Tracker.
      </footer>
      {drawer && <CourseDrawer code={drawer} year={YEAR} planned={planned.get(drawer)} onClose={() => setDrawer(null)} />}
    </div>
  );
}

function Hero() {
  return (
    <div className="panel hero">
      <span className="eyebrow">Semester-by-semester degree planning</span>
      <h1>Your path to graduation, solved.</h1>
      <p className="lede">
        Tell CoursePilot where you are: courses taken, AP/IB scores, transfer hours. It builds a full plan to
        graduation that respects every prerequisite chain, credit limit, and degree rule it models, and explains
        exactly why when a goal isn't possible.
      </p>
      <ul className="features">
        <li><b>Real catalog data</b><span>10,673 UNC courses and the official requirement tables, each linked to its source.</span></li>
        <li><b>Constraint-optimized</b><span>Google OR-Tools CP-SAT finds the minimum coursework, then balances your semesters.</span></li>
        <li><b>Honest about uncertainty</b><span>Verified vs. uncertain rules are labeled. Nothing is ever "certified".</span></li>
      </ul>
      <p className="hint">Start with step 1 on the left. The Mathematics B.A. and Economics B.A. are fully reviewed, alone or as a
        double major; more majors are coming.</p>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="skeleton" aria-label="Building your plan">
      <div className="sk-line wide" />
      <div className="sk-grid">{Array.from({ length: 6 }, (_, i) => <div key={i} className="sk-card" />)}</div>
      <p className="hint center">Solving with CP-SAT: checking prerequisites, credit limits, and requirements…</p>
    </div>
  );
}
