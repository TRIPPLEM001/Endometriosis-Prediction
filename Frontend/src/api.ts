// The connection between the Enara screens and the screening backend.
// The backend address can be changed with VITE_API_URL; by default it is the
// backend started with "docker compose up".

const API_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://127.0.0.1:8000";

// Must match the backend's CONSENT_VERSION setting.
const CONSENT_VERSION = "2026-10-v1";

export type Recommendation =
  | "low_risk"
  | "elevated_needs_labs"
  | "elevated_confirmed"
  | "elevated_not_confirmed";

export type Factor = { feature: string; label: string; direction: string };

// What the backend sends back after a screening.
export type Screening = {
  id: string;
  created_at: string;
  recommendation: Recommendation;
  tier1_probability: number;
  tier1_flagged: boolean;
  tier2_probability: number | null;
  tier2_flagged: boolean | null;
  tier1_probability_display: string;
  tier2_probability_display: string | null;
  can_add_labs: boolean;
  next_step: string;
  disclaimer: string;
  prototype_notice: string | null;
  report_text: string;
  factors: Record<string, Factor[]>;
};

// What we send for Tier 1 (the backend's field names).
export type SymptomPayload = {
  Age: number;
  BMI: number;
  Cycle_Length: number;
  Age_of_Menarche: number;
  Dysmenorrhea_Score: number;
  Pelvic_Pain_Score: number;
  Dyspareunia_Score: number;
  Dyschezia_Score: number;
  Urinary_Symptoms_Score: number;
  Mental_Health_Score: number;
  Family_History: boolean;
  Infertility_Status: boolean;
};

export type LabPayload = { CA_125_Level: number; CRP_Level: number };

// Friendly names for the messages shown when the backend rejects a value.
const FIELD_NAMES: Record<string, string> = {
  Age: "Age",
  BMI: "BMI",
  Cycle_Length: "Cycle length",
  Age_of_Menarche: "Age at first period",
  Dysmenorrhea_Score: "Period pain",
  Pelvic_Pain_Score: "Pelvic pain",
  Dyspareunia_Score: "Pain during or after sex",
  Dyschezia_Score: "Painful bowel movements",
  Urinary_Symptoms_Score: "Urinary symptoms",
  Mental_Health_Score: "Mental wellbeing",
  CA_125_Level: "CA-125",
  CRP_Level: "CRP",
  email: "Email address",
  password: "Password",
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

function describe(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      const where = Array.isArray(item?.loc) ? String(item.loc[item.loc.length - 1]) : "";
      const name = FIELD_NAMES[where] ?? where;
      const msg = typeof item?.msg === "string" ? item.msg : "is not valid";
      return name ? `${name}: ${msg}` : msg;
    });
    if (parts.length) return parts.join(". ");
  }
  return `Something went wrong (code ${status}). Please try again.`;
}

// The login token lives only in memory, so closing or refreshing the page signs the user out.
let token: string | null = null;
let onUnauthorized: (() => void) | null = null;

// Called when the backend says the session has ended (tokens last 30 minutes).
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const isAuthCall = path.startsWith("/auth/login") || path.startsWith("/auth/register");
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (token && !isAuthCall) headers["Authorization"] = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(API_URL + path, {
      method: options.method ?? "GET",
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch (error) {
    console.error("Could not reach the backend at", API_URL, error);
    throw new ApiError(
      "We can’t reach the service right now. Please check your connection and try again.",
      0,
    );
  }

    if (response.status === 401 && token && !isAuthCall && !(path === "/account" && options.method === "DELETE")) {
    token = null;
    onUnauthorized?.();
    throw new ApiError("Your session has ended. Please sign in again.", 401);
  }

  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = (await response.json()).detail;
    } catch {
      // the response had no readable message
    }
    throw new ApiError(describe(detail, response.status), response.status);
  }
    const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export async function register(email: string, password: string): Promise<void> {
  await request("/auth/register", {
    method: "POST",
    body: {
      email,
      password,
      consent_accepted: true,
      consent_version: CONSENT_VERSION,
    },
  });
}

export async function login(email: string, password: string): Promise<void> {
  const data = await request<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
  token = data.access_token;
}

export function createScreening(answers: SymptomPayload): Promise<Screening> {
  return request<Screening>("/screenings", { method: "POST", body: answers });
}

export function addLabs(screeningId: string, labs: LabPayload): Promise<Screening> {
  return request<Screening>(`/screenings/${screeningId}/labs`, { method: "POST", body: labs });
}


export function exportAccount(): Promise<unknown> {
  return request<unknown>("/account/export");
}

export async function deleteAccount(password: string): Promise<void> {
  await request<void>("/account", { method: "DELETE", body: { password } });
  token = null;
}


export function signOut() {
  token = null;
}

// The short version of a screening, as shown in the "My results" list.
export type ScreeningSummary = {
  id: string;
  created_at: string;
  updated_at: string;
  recommendation: Recommendation;
  tier1_probability: number;
  tier1_flagged: boolean;
  tier2_probability: number | null;
  tier2_flagged: boolean | null;
  tier1_probability_display: string;
  tier2_probability_display: string | null;
  can_add_labs: boolean;
};

export type ScreeningList = {
  items: ScreeningSummary[];
  total: number;
  limit: number;
  offset: number;
};

export function listScreenings(limit = 20, offset = 0): Promise<ScreeningList> {
  return request<ScreeningList>(`/screenings?limit=${limit}&offset=${offset}`);
}

export function getScreening(id: string): Promise<Screening> {
  return request<Screening>(`/screenings/${id}`);
}

export function deleteScreening(id: string): Promise<void> {
  return request<void>(`/screenings/${id}`, { method: "DELETE" });
}