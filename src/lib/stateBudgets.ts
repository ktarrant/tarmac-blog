export interface GovernorTerm {
  name: string;
  party: "D" | "R" | "I" | null;
  start: string;
  end: string | null;
}

export interface Anomaly {
  year: number;
  metric: string;
  previous: number;
  amount: number;
  change: number;
  kind: "spike" | "level_shift" | "census_schema_change" | "suspected_coding_error";
  impact: number;
}

export interface Disaster {
  number: number;
  title: string;
  type: string;
  declared: string;
  major: boolean;
  federal_obligated: number;
  individual_approved: number;
}

export interface StateData {
  abbr: string;
  name: string;
  years: number[];
  fiscal_year_start_month: number;
  population: number[];
  expenditure_by_function: Record<string, number[]>;
  expenditure_by_component: Record<string, number[]>;
  revenue_by_source: Record<string, number[]>;
  debt: Record<string, number[]>;
  debt_by_purpose: Record<string, number[]>;
  spending_split: { operating: number[]; capital: number[] };
  capital_by_function: Record<string, number[]>;
  debt_service: number[];
  governors: GovernorTerm[];
  anomalies: Anomaly[];
  disasters: Record<string, Disaster[]>;
}

/** Sentence-case label for a pipeline key like "public_welfare". */
export function label(key: string): string {
  const overrides: Record<string, string> = {
    k12: "K-12 education",
    higher_education: "Higher education",
    public_welfare: "Public welfare & Medicaid",
    health_and_hospitals: "Health & hospitals",
    housing_and_community: "Housing & community",
    natural_resources: "Natural resources",
    parks_and_recreation: "Parks & recreation",
    public_safety: "Public safety",
    education_other: "Other education",
    commercial_and_insurance: "Commercial & insurance programs",
    federal_aid: "Federal aid",
    misc_general_revenue: "Miscellaneous",
    local_aid_received: "Local transfers",
    outstanding_end: "Outstanding",
    outstanding_beginning: "Outstanding (start of year)",
    aid_to_local: "Aid to local government",
    aid_to_school_districts: "Aid to school districts",
    aid_to_state_governments: "Aid to other states",
    current_operations: "Current operations",
    capital_other: "Capital (other)",
    interest_on_debt: "Interest on debt",
  };
  if (overrides[key]) return overrides[key];
  const spaced = key.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** The metric key inside an anomaly, e.g. "expenditure.k12" -> "K-12 education". */
export function anomalyLabel(metric: string): string {
  const [flow, key] = metric.split(".");
  if (flow === "spending") {
    return key === "capital" ? "Capital spending" : "Operating spending";
  }
  const flowLabel = { expenditure: "Spending", revenue: "Revenue", debt: "Debt" }[flow] ?? flow;
  return `${flowLabel} · ${label(key)}`;
}

/** Which side of the budget a movement sits on — what a reader needs in order
 *  to tell a reallocation from something that gets paid for by borrowing. */
export function budgetSide(metric: string): "operating" | "capital" | "borrowing" | "revenue" {
  if (metric === "spending.capital") return "capital";
  if (metric.startsWith("debt.")) return "borrowing";
  if (metric.startsWith("revenue.")) return "revenue";
  return "operating";
}

export const SIDE_NOTE: Record<string, string> = {
  operating: "Operating budget — has to balance, so this is money moved rather than money borrowed",
  capital: "Capital — building things, which is what borrowing pays for",
  borrowing: "Borrowing — changes what the state owes, not what it spends running",
  revenue: "Revenue — money coming in",
};

export const PARTY_NAMES: Record<string, string> = {
  D: "Democrat",
  R: "Republican",
  I: "Independent",
};

/** Governor in office on the reference date used for a fiscal year. */
export function governorForYear(
  governors: GovernorTerm[],
  year: number,
  fiscalStartMonth: number
): GovernorTerm | undefined {
  // Mid-year point of the fiscal year, so a handover in January doesn't
  // reassign the whole year to an incoming governor.
  const startYear = fiscalStartMonth > 1 ? year - 1 : year;
  const reference = new Date(Date.UTC(startYear, fiscalStartMonth - 1 + 6, 1));
  return governors.find((term) => {
    const start = new Date(term.start);
    const end = term.end ? new Date(term.end) : new Date(8640000000000000);
    return start <= reference && reference <= end;
  });
}
