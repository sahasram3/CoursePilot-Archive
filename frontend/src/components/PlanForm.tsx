import { useEffect, useState } from "react";
import { api } from "../api";
import { addRegularTerms, regularTerms, termKey } from "../terms";
import type { CompletedCourse, Lock, Placement, ProgramListing } from "../types";
import { CourseInput } from "./CourseInput";

export interface FormState {
  program: string;
  entryTerm: string;
  firstTerm: string;
  graduationTerm: string;
  includeSummer: boolean;
  maxCredits: number;
  targetProgramCredits: number;
  completed: CompletedCourse[];
  tokens: string[];
  locks: Lock[];
  exclude: string[];
  alternatives: number;
}

interface Props {
  year: string;
  programs: ProgramListing[];
  form: FormState;
  setForm: (f: FormState) => void;
  onSubmit: () => void;
  busy: boolean;
}

const ENTRY_TERMS = regularTerms("Fall 2022", "Fall 2026");

export function PlanForm({ year, programs, form, setForm, onSubmit, busy }: Props) {
  const [placements, setPlacements] = useState<Placement[]>([]);
  const set = (patch: Partial<FormState>) => setForm({ ...form, ...patch });
  const majors = programs.filter((p) => p.kind === "major");
  const ready = majors.filter((p) => p.plannable);
  const pending = majors.filter((p) => !p.plannable);
  const minorsCount = programs.filter((p) => p.kind === "minor").length;

  useEffect(() => {
    if (!form.program) return;
    api.placements(form.program, year).then((r) => setPlacements(r.placements)).catch(() => setPlacements([]));
  }, [form.program, year]);

  const firstOptions = regularTerms(form.entryTerm, addRegularTerms(form.entryTerm, 9));
  const gradOptions = regularTerms(form.firstTerm, addRegularTerms(form.firstTerm, 10))
    .filter((t) => termKey(t) >= termKey(form.firstTerm));

  return (
    <form className="panel form" onSubmit={(e) => { e.preventDefault(); onSubmit(); }}>
      <section>
        <h2><span className="step">1</span> Program</h2>
        <label htmlFor="program">Major</label>
        <select id="program" value={form.program} onChange={(e) => set({ program: e.target.value, locks: [], exclude: [] })}>
          <optgroup label="Reviewed — ready to plan">
            {ready.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </optgroup>
          <optgroup label="Not yet reviewed — coming soon">
            {pending.map((p) => <option key={p.id} value={p.id} disabled>{p.name}</option>)}
          </optgroup>
        </select>
        <p className="hint">
          {ready.length} of {majors.length} majors reviewed so far · {minorsCount} minors in the catalog.
          Double majors and minors become available as programs are reviewed.
        </p>
      </section>

      <section>
        <h2><span className="step">2</span> Timeline</h2>
        <div className="grid3">
          <div>
            <label htmlFor="entry">Started at UNC</label>
            <select id="entry" value={form.entryTerm} onChange={(e) => {
              const entryTerm = e.target.value;
              const firstTerm = termKey(form.firstTerm) < termKey(entryTerm) ? entryTerm : form.firstTerm;
              set({ entryTerm, firstTerm });
            }}>
              {ENTRY_TERMS.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="first">Plan from</label>
            <select id="first" value={form.firstTerm} onChange={(e) => {
              const firstTerm = e.target.value;
              const graduationTerm = termKey(form.graduationTerm) < termKey(firstTerm) ? firstTerm : form.graduationTerm;
              set({ firstTerm, graduationTerm, locks: [] });
            }}>
              {firstOptions.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="grad">Graduate in</label>
            <select id="grad" value={form.graduationTerm} onChange={(e) => set({ graduationTerm: e.target.value, locks: [] })}>
              {gradOptions.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
        </div>
        <label className="check">
          <input type="checkbox" checked={form.includeSummer} onChange={(e) => set({ includeSummer: e.target.checked })} />
          Allow summer terms (used only if needed)
        </label>
      </section>

      <section>
        <h2><span className="step">3</span> Courses you have credit for</h2>
        <CourseInput year={year} courses={form.completed} onChange={(completed) => set({ completed })} />
        {placements.length > 0 && (
          <div className="placements">
            <span className="label">Department placement</span>
            {placements.map((p) => (
              <label key={p.token} className="check">
                <input type="checkbox" checked={form.tokens.includes(p.token)} onChange={(e) =>
                  set({ tokens: e.target.checked ? [...form.tokens, p.token] : form.tokens.filter((t) => t !== p.token) })} />
                {p.label}
              </label>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2><span className="step">4</span> Preferences</h2>
        <div className="grid2">
          <div>
            <label htmlFor="maxcr">Max credits per semester</label>
            <select id="maxcr" value={form.maxCredits} onChange={(e) => set({ maxCredits: Number(e.target.value) })}>
              {[15, 16, 17, 18].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="target">Program credits per semester (target)</label>
            <select id="target" value={form.targetProgramCredits} onChange={(e) => set({ targetProgramCredits: Number(e.target.value) })}>
              {[4, 6, 7, 8, 10, 12].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        </div>
        {(form.locks.length > 0 || form.exclude.length > 0) && (
          <div className="pins">
            {form.locks.map((l) => (
              <span key={l.code} className="pin">📌 {l.code} in {l.term}
                <button type="button" className="icon" aria-label={`Unlock ${l.code}`}
                        onClick={() => set({ locks: form.locks.filter((x) => x.code !== l.code) })}>×</button></span>
            ))}
            {form.exclude.map((c) => (
              <span key={c} className="pin avoid">Avoid {c}
                <button type="button" className="icon" aria-label={`Stop avoiding ${c}`}
                        onClick={() => set({ exclude: form.exclude.filter((x) => x !== c) })}>×</button></span>
            ))}
          </div>
        )}
      </section>

      <button className="primary" type="submit" disabled={busy || !form.program}>
        {busy ? "Planning…" : "Build my semester plan"}
      </button>
    </form>
  );
}
