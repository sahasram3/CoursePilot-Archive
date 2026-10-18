import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { CourseDrawer } from "./components/CourseDrawer";
import { FormState, PlanForm } from "./components/PlanForm";
import { Issues, PlanView } from "./components/PlanView";
import { addRegularTerms, nextRegularTerm } from "./terms";
import type { PlanRequest, PlanResponse, ProgramListing } from "./types";

const YEAR = "2026-2027";
const STORAGE_KEY = "prereqpath.form.v1";

function defaultForm(): FormState {
  const first = nextRegularTerm();
  return {
    program: "mathematics-major-ba", entryTerm: "Fall 2026", firstTerm: first,
    graduationTerm: addRegularTerms("Fall 2026", 7), includeSummer: false, maxCredits: 18,
    targetProgramCredits: 8, completed: [], tokens: [], locks: [], exclude: [], alternatives: 2,
  };
}

function loadForm(): FormState {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return { ...defaultForm(), ...JSON.parse(saved) };
  } catch { /* storage unavailable: use defaults */ }
  return defaultForm();
}

function toRequest(f: FormState): PlanRequest {
  return {
    catalog_year: YEAR, programs: [f.program], entry_term: f.entryTerm, first_term: f.firstTerm,
    graduation_term: f.graduationTerm, include_summer: f.includeSummer, min_credits: 12,
    max_credits: f.maxCredits, target_program_credits: f.targetProgramCredits,
    completed: f.completed.map(({ code, grade, origin, in_progress }) => ({ code, grade, origin, in_progress })),
    tokens: f.tokens, locks: f.locks, exclude: f.exclude, alternatives: f.alternatives,
  };
}

export default function App() {
  const [programs, setPrograms] = useState<ProgramListing[]>([]);
  const [form, setForm] = useState<FormState>(loadForm);
  const [response, setResponse] = useState<PlanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [drawer, setDrawer] = useState<string | null>(null);

  useEffect(() => {
    api.programs(YEAR).then((r) => setPrograms(r.programs)).catch((e: Error) => setError(e.message));
  }, []);
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(form)); } catch { /* ignore */ }
  }, [form]);

  const run = useCallback(async (f: FormState) => {
    setBusy(true);
    setError(null);
    try {
      setResponse(await api.plan(toRequest(f)));
    } catch (e) {
      setResponse(null);
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, []);

  const updateAndRun = (patch: Partial<FormState>) => {
    const next = { ...form, ...patch };
    setForm(next);
    run(next);
  };

  return (
    <div className="app">
      <header className="top">
        <div className="brand"><span className="logo">P</span> PreReqPath</div>
        <div className="sub">Semester-by-semester planning from the UNC-Chapel Hill {YEAR} catalog</div>
      </header>
      <main>
        <PlanForm year={YEAR} programs={programs} form={form} setForm={setForm} busy={busy} onSubmit={() => run(form)} />
        <div className="output">
          {error && <div className="banner error" role="alert">{error}</div>}
          {!response && !error && (
            <div className="panel empty">
              <h2>Your plan will appear here</h2>
              <p>Pick your program and timeline, add courses you already have credit for (including AP and
                courses in progress), and build a plan. Every requirement links to its catalog source.</p>
            </div>
          )}
          {response?.status === "infeasible" && response.infeasibility && (
            <div className="panel infeasible">
              <h2>No plan fits these constraints</h2>
              <p>{response.infeasibility.summary}</p>
              <h3>Why</h3>
              <ul>{response.infeasibility.causes.map((c) => <li key={c}>{c}</li>)}</ul>
              <h3>What would work</h3>
              <ul className="suggestions">{response.infeasibility.suggestions.map((s) => <li key={s}>{s}</li>)}</ul>
              <Issues issues={response.issues} />
            </div>
          )}
          {response?.status === "feasible" && (
            <PlanView
              response={response}
              locked={new Set(form.locks.map((l) => l.code))}
              onShowCourse={setDrawer}
              onLock={(code, term) => {
                const exists = form.locks.some((l) => l.code === code);
                updateAndRun({ locks: exists ? form.locks.filter((l) => l.code !== code) : [...form.locks, { code, term }] });
              }}
              onAvoid={(code) => updateAndRun({
                exclude: [...form.exclude, code], locks: form.locks.filter((l) => l.code !== code),
              })}
            />
          )}
        </div>
      </main>
      <footer>
        PreReqPath is an independent student project, not affiliated with or endorsed by UNC-Chapel Hill.
        Plans are provisional; confirm with your academic advisor and Tar Heel Tracker.
      </footer>
      {drawer && <CourseDrawer code={drawer} year={YEAR} onClose={() => setDrawer(null)} />}
    </div>
  );
}
