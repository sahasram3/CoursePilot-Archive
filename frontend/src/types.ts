// Mirrors backend/prereqpath/planner/schemas.py and the /api responses.

export type Origin = "unc" | "transfer" | "exam";

export interface CompletedCourse {
  code: string;
  title?: string;
  grade: string | null;
  origin: Origin;
  in_progress: boolean;
}

export interface Lock {
  code: string;
  term: string;
}

export interface ExamScore {
  type: "AP" | "IB";
  exam: string;
  score: number;
}

export interface OtherCredit {
  label: string;
  hours: number;
  origin: "transfer" | "exam";
}

export interface ExamAward {
  type: "AP" | "IB";
  exam: string;
  min_score: number;
  courses: string[];
  other_credit: string[];
  hours: number;
  note?: string;
}

export interface ExamCatalog {
  source_url: string;
  exams: { type: "AP" | "IB"; exam: string; min_scores: number[] }[];
  awards: ExamAward[];
}

export interface PlanRequest {
  catalog_year: string;
  programs: string[];
  entry_term: string;
  first_term: string;
  graduation_term: string;
  include_summer: boolean;
  min_credits: number;
  max_credits: number;
  target_program_credits: number;
  completed: Omit<CompletedCourse, "title">[];
  exams: ExamScore[];
  other_credit: OtherCredit[];
  tokens: string[];
  locks: Lock[];
  exclude: string[];
  alternatives: number;
}

export interface ProgramListing {
  id: string;
  name: string;
  kind: "major" | "minor";
  degree?: string;
  url: string;
  concentration_of?: string;
  plannable: boolean;
  verification: string | null;
}

export interface Placement {
  token: string;
  course: string;
  title: string;
  label: string;
}

export interface CourseHit {
  code: string;
  title: string;
  credits_min: number;
  credits_max: number;
}

export interface Issue {
  severity: "info" | "warning" | "blocker";
  code: string;
  message: string;
  source_url?: string | null;
  course?: string | null;
}

export interface PlannedCourse {
  code: string;
  title: string;
  credits: number;
  reasons: string[];
  requirement_ids: string[];
  contingencies: string[];
  warnings: string[];
  requisites_status: string;
  requisites_raw?: string | null;
  prerequisites_text: string;
  satisfied_by: string[];
  gen_ed: string[];
  source_url: string;
}

export interface StartingCredit {
  code: string | null;
  title: string;
  credits: number;
  grade: string | null;
  origin: Origin;
  in_progress: boolean;
  source: string;
}

export interface PlannedTerm {
  term: string;
  courses: PlannedCourse[];
  course_credits: number;
  unassigned_credits: number;
  total_credits: number;
}

export interface RequirementStatus {
  id: string;
  label: string;
  kind: string;
  status: "completed" | "planned" | "uncertain" | "unmet" | "not_needed";
  courses: { code: string; term: string | null; completed: boolean }[];
  core: boolean;
  min_hours?: number | null;
  count?: number | null;
  source: { url: string; catalog_year: string; section?: string; text?: string };
  verification: { status: string; by?: string | null; on?: string | null; notes: string[] };
  children: RequirementStatus[];
}

export interface Plan {
  terms: PlannedTerm[];
  requirements: Record<string, RequirementStatus[]>;
  summary: {
    completed_hours: number;
    planned_course_hours: number;
    unassigned_gen_ed_elective_hours: number;
    projected_total_hours: number;
    countable_hours_after_ba_cap: number;
    ba_subject_cap_applies: boolean;
    subjects_over_45_hours: string[];
    unc_hours_projected: number;
    transfer_hours: number;
    credit_by_exam_hours: number;
    regular_semesters_entry_to_graduation: number;
    graduation_term: string;
    major_core: Record<string, { core_hours: number; core_hours_at_unc_projected: number; half_at_unc_ok: boolean }>;
  };
}

export interface PlanResponse {
  status: "feasible" | "infeasible";
  plan_status: "provisional";
  graduation_certified: false;
  certification_note: string;
  catalog_year: string;
  programs: { id: string; name: string; kind: string; degree?: string; url: string;
              verification: { status: string; by?: string; on?: string } }[];
  completed_courses: StartingCredit[];
  plans: Plan[];
  infeasibility: {
    summary: string; causes: string[]; suggestions: string[];
    actions: { label: string; changes: Partial<Record<string, unknown>> }[];
  } | null;
  issues: Issue[];
  not_modeled: string[];
  solver: { engine: string; seconds: number; statuses: string[] };
}

export interface CourseDetail {
  code: string;
  title: string;
  credits_min: number;
  credits_max: number;
  description: string;
  gen_ed: string[];
  requisites_raw?: string;
  requisites_status: string;
  requisites_notes: string[];
  prerequisites_text: string;
  corequisites_text: string | null;
  same_as: string[];
  source: { url: string; catalog_year: string };
}
