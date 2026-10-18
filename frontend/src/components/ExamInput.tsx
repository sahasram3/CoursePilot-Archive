import { useMemo, useState } from "react";
import type { ExamAward, ExamCatalog, ExamScore, OtherCredit } from "../types";

interface Props {
  catalog: ExamCatalog | null;
  exams: ExamScore[];
  onExams: (exams: ExamScore[]) => void;
  other: OtherCredit[];
  onOther: (other: OtherCredit[]) => void;
}

export function awardFor(catalog: ExamCatalog | null, e: ExamScore): ExamAward | null {
  if (!catalog) return null;
  const rows = catalog.awards.filter((a) => a.type === e.type && a.exam === e.exam && a.min_score <= e.score);
  return rows.sort((a, b) => b.min_score - a.min_score)[0] ?? null;
}

export function describeAward(award: ExamAward | null): string {
  if (!award) return "No credit at this score";
  const parts = [...award.courses, ...award.other_credit];
  return `${parts.join(", ")}${award.hours ? ` · ${award.hours} hrs` : " · placement only"}`;
}

export function ExamInput({ catalog, exams, onExams, other, onOther }: Props) {
  const [type, setType] = useState<"AP" | "IB">("AP");
  const [exam, setExam] = useState("");
  const [score, setScore] = useState(5);
  const [hours, setHours] = useState("");
  const [label, setLabel] = useState("");

  const options = useMemo(() => (catalog?.exams ?? []).filter((e) => e.type === type), [catalog, type]);
  const maxScore = type === "AP" ? 5 : 7;
  const preview = exam ? awardFor(catalog, { type, exam, score }) : null;

  const addExam = () => {
    if (!exam) return;
    onExams([...exams.filter((e) => !(e.type === type && e.exam === exam)), { type, exam, score }]);
    setExam("");
  };
  const addOther = () => {
    const h = Number(hours);
    if (!(h > 0 && h <= 90)) return;
    onOther([...other, { label: label.trim() || "Transfer credit", hours: h, origin: "transfer" }]);
    setHours("");
    setLabel("");
  };

  return (
    <div className="exam-input">
      <div className="exam-row">
        <select aria-label="Exam program" value={type} onChange={(e) => { setType(e.target.value as "AP" | "IB"); setExam(""); setScore(e.target.value === "AP" ? 5 : 7); }}>
          <option value="AP">AP</option>
          <option value="IB">IB</option>
        </select>
        <select aria-label="Exam" value={exam} onChange={(e) => setExam(e.target.value)} className="grow">
          <option value="">{catalog ? "Select exam" : "Loading…"}</option>
          {options.map((o) => <option key={o.exam} value={o.exam}>{o.exam}</option>)}
        </select>
        <select aria-label="Score" value={score} onChange={(e) => setScore(Number(e.target.value))}>
          {Array.from({ length: maxScore }, (_, i) => maxScore - i).map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <button type="button" className="secondary" onClick={addExam} disabled={!exam}>Add</button>
      </div>
      {exam && (
        <p className={`award-preview ${preview && preview.hours ? "" : "muted"}`}>
          UNC awards: {describeAward(preview)}
          {preview?.note && <span className="note"> {preview.note}</span>}
        </p>
      )}
      {exams.length > 0 && (
        <ul className="chips">
          {exams.map((e) => (
            <li key={`${e.type}-${e.exam}`} className="chip-row">
              <span><b>{e.type} {e.exam}</b> · score {e.score}</span>
              <small>{describeAward(awardFor(catalog, e))}</small>
              <button type="button" className="icon" aria-label={`Remove ${e.exam}`}
                      onClick={() => onExams(exams.filter((x) => x !== e))}>×</button>
            </li>
          ))}
        </ul>
      )}
      <details className="other-credit" open={other.length > 0}>
        <summary>Transfer hours without a UNC course equivalent</summary>
        <div className="exam-row">
          <input type="text" placeholder="Label, e.g. Community college" value={label} maxLength={80}
                 aria-label="Transfer credit label" onChange={(e) => setLabel(e.target.value)} className="grow" />
          <input type="number" min={1} max={90} step={0.5} placeholder="Hours" value={hours}
                 aria-label="Transfer credit hours" onChange={(e) => setHours(e.target.value)} className="hours" />
          <button type="button" className="secondary" onClick={addOther} disabled={!(Number(hours) > 0)}>Add</button>
        </div>
        {other.length > 0 && (
          <ul className="chips">
            {other.map((o, i) => (
              <li key={i} className="chip-row">
                <span><b>{o.label}</b></span><small>{o.hours} hrs · counts toward 120 only</small>
                <button type="button" className="icon" aria-label={`Remove ${o.label}`}
                        onClick={() => onOther(other.filter((_, j) => j !== i))}>×</button>
              </li>
            ))}
          </ul>
        )}
      </details>
      {catalog && (
        <p className="hint">Awards come from the <a href={catalog.source_url} target="_blank" rel="noreferrer">UNC catalog credit table ↗</a>.</p>
      )}
    </div>
  );
}
