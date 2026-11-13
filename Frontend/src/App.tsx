import { FormEvent, ReactNode, useEffect, useState } from "react";
import * as api from "./api";
import { legalDocs, type LegalDoc } from "./legal";

type Screen =
  | "welcome"
  | "login"
  | "signup"
  | "profile"
  | "assessment"
  | "result"
  | "history"
  | "mydata";

type Answers = {
  age: string;
  bmi: string;
  cycleLength: string;
  menarcheAge: string;
  dysmenorrhea: number;
  pelvicPain: number;
  dyspareunia: number;
  dyschezia: number;
  urinary: number;
  familyHistory: string;
  infertility: string;
  mentalHealth: number;
};

const initialAnswers: Answers = {
  age: "",
  bmi: "",
  cycleLength: "",
  menarcheAge: "",
  dysmenorrhea: 0,
  pelvicPain: 0,
  dyspareunia: 0,
  dyschezia: 0,
  urinary: 0,
  familyHistory: "",
  infertility: "",
  mentalHealth: 5,
};

const assessmentSections = [
  {
    eyebrow: "Your cycle",
    title: "Tell us about your body",
    description:
      "These details help establish your baseline. Estimates are completely fine.",
  },
  {
    eyebrow: "Your symptoms",
    title: "How have you been feeling?",
    description:
      "Rate each symptom based on your experience over the last three months.",
  },
  {
    eyebrow: "Health history",
    title: "A little more context",
    description:
      "Your family history and wellbeing can add useful context to your assessment.",
  },
];

const icons: Record<string, ReactNode> = {
  flower: (
    <>
      <path d="M12 12c-4-1-5-5-3-7 2-2 5 0 3 7Z" />
      <path d="M12 12c1-4 5-5 7-3 2 2 0 5-7 3Z" />
      <path d="M12 12c4 1 5 5 3 7-2 2-5 0-3-7Z" />
      <path d="M12 12c-1 4-5 5-7 3-2-2 0-5 7-3Z" />
      <circle cx="12" cy="12" r="1.5" />
    </>
  ),
  arrow: <path d="m9 18 6-6-6-6" />,
  back: <path d="m15 18-6-6 6-6" />,
    menu: <path d="M4 7h16M4 12h16M4 17h16" />,
      eye: (
    <>
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  eyeoff: (
    <>
      <path d="M3 3l18 18" />
      <path d="M10.6 5.1A10.3 10.3 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3.2 4.2M6.6 6.6A17 17 0 0 0 2 12s3.5 7 10 7c1.8 0 3.4-.5 4.8-1.2" />
      <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
    </>
  ),
  mail: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="3" />
      <path d="m4 7 8 6 8-6" />
    </>
  ),
  lock: (
    <>
      <rect x="4" y="10" width="16" height="11" rx="3" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </>
  ),
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="3" />
      <path d="M8 3v4m8-4v4M3 10h18" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  shield: (
    <>
      <path d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6l-7-3Z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  spark: (
    <>
      <path d="m12 3 1.4 4.1L17 9l-3.6 1.9L12 15l-1.4-4.1L7 9l3.6-1.9L12 3Z" />
      <path d="m18.5 15 .7 2.1L21 18l-1.8.9-.7 2.1-.7-2.1L16 18l1.8-.9.7-2.1Z" />
    </>
  ),
};

function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {icons[name]}
    </svg>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="brand">
      <span className="brand-mark">
        <Icon name="flower" size={compact ? 18 : 23} />
      </span>
      <span className={compact ? "brand-name brand-name-small" : "brand-name"}>
        Enara
      </span>
    </div>
  );
}

function AuthHeader({
  onBack,
  step,
}: {
  onBack: () => void;
  step?: string;
}) {
  return (
    <header className="topbar">
      <button className="icon-button" onClick={onBack} aria-label="Go back">
        <Icon name="back" />
      </button>
      {step ? <span className="topbar-step">{step}</span> : <Brand compact />}
      <span className="icon-spacer" />
    </header>
  );
}

function AppMenu({
  onHome,
  onResults,
  onData,
  onSignOut,
}: {
  onHome: () => void;
  onResults: () => void;
  onData: () => void;
  onSignOut: () => void;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  function choose(action: () => void) {
    setOpen(false);
    action();
  }

  return (
    <div className="menu-wrap">
      <button
        className="icon-button"
        onClick={() => setOpen(!open)}
        aria-label="Open menu"
        aria-expanded={open}
      >
        <Icon name="menu" />
      </button>
      {open && (
        <div className="menu-panel" role="menu">
          <button className="menu-item" role="menuitem" onClick={() => choose(onHome)}>
            New assessment
          </button>
          <button className="menu-item" role="menuitem" onClick={() => choose(onResults)}>
            My results
          </button>
          <button className="menu-item" role="menuitem" onClick={() => choose(onData)}>
            My data
          </button>
          <div className="menu-divider" />
          <button
            className="menu-item menu-item-danger"
            role="menuitem"
            onClick={() => choose(onSignOut)}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  name,
  type = "text",
  placeholder,
  icon,
  suffix,
  value,
  onChange,
  required = true,
  min,
  max,
  step,
  minLength,
}: {
  label: string;
  name: string;
  type?: string;
  placeholder?: string;
  icon?: string;
  suffix?: string;
  value?: string;
  onChange?: (value: string) => void;
  required?: boolean;
  min?: string;
  max?: string;
  step?: string;
  minLength?: number;
}) {
  const [visible, setVisible] = useState(false);
  const isPassword = type === "password";
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <span className="input-wrap">
        {icon && (
          <span className="input-icon">
            <Icon name={icon} size={19} />
          </span>
        )}
        <input
          name={name}
          type={isPassword && visible ? "text" : type}
          placeholder={placeholder}
          value={value}
          onChange={onChange ? (event) => onChange(event.target.value) : undefined}
          required={required}
          min={min}
          max={max}
          step={step}
          minLength={minLength}
          className={
            (icon ? "has-icon" : suffix ? "has-suffix" : "") +
            (isPassword ? " has-toggle" : "")
          }
        />
        {suffix && <span className="input-suffix">{suffix}</span>}
        {isPassword && (
          <button
            type="button"
            className="input-toggle"
            onClick={() => setVisible(!visible)}
            aria-label={visible ? "Hide password" : "Show password"}
          >
            <Icon name={visible ? "eyeoff" : "eye"} size={19} />
          </button>
        )}
      </span>
    </label>
  );
}

function Welcome({
  onLogin,
  onSignup,
}: {
  onLogin: () => void;
  onSignup: () => void;
}) {
  return (
    <section className="welcome-screen">
      <div className="welcome-visual">
        <div className="visual-orbit orbit-one" />
        <div className="visual-orbit orbit-two" />
        <div className="petal petal-one" />
        <div className="petal petal-two" />
        <div className="petal petal-three" />
        <div className="welcome-brand">
          <span className="welcome-mark">
            <Icon name="flower" size={34} />
          </span>
          <span>Enara</span>
        </div>
      </div>
      <div className="welcome-content">
        <p className="eyebrow">Understand your symptoms</p>
        <h1>Clarity starts with listening to your body.</h1>
        <p className="lead">
          A private, guided assessment to help you better understand your
          endometriosis risk.
        </p>
        <div className="button-stack">
          <button className="primary-button" onClick={onLogin}>
            Sign in
            <Icon name="arrow" size={19} />
          </button>
          <button className="secondary-button" onClick={onSignup}>
            Create an account
          </button>
        </div>
        <p className="privacy-note">
          <Icon name="shield" size={15} />
          Your health information stays private
        </p>
      </div>
    </section>
  );
}

function Login({
  onBack,
  onSignIn,
  onSignup,
  notice,
}: {
  onBack: () => void;
  onSignIn: (email: string, password: string) => Promise<void>;
  onSignup: () => void;
  notice: string;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError("");
    setBusy(true);
    try {
      await onSignIn(
        String(form.get("email") ?? "").trim(),
        String(form.get("password") ?? ""),
      );
    } catch (err) {
      setError(api.messageOf(err));
      setBusy(false);
    }
  }

  return (
    <>
      <AuthHeader onBack={onBack} />
      <main className="screen-content auth-content">
        <div className="title-block">
          <p className="eyebrow">Welcome back</p>
          <h1>Sign in to Enara</h1>
          <p>Continue your private health assessment.</p>
        </div>
        <form onSubmit={submit} className="form-stack">
          <Field
            label="Email address"
            name="email"
            type="email"
            placeholder="you@example.com"
            icon="mail"
          />
          <Field
            label="Password"
            name="password"
            type="password"
            placeholder="Enter your password"
            icon="lock"
          />
          <button type="button" className="text-button forgot-button">
            Forgot password?
          </button>
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : (
            notice && (
              <p className="form-notice" role="status">
                {notice}
              </p>
            )
          )}
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
            <Icon name="arrow" size={19} />
          </button>
        </form>
        <p className="auth-switch">
          New to Enara?{" "}
          <button className="text-button" onClick={onSignup}>
            Create account
          </button>
        </p>
      </main>
    </>
  );
}

function LegalSheet({ doc, onClose }: { doc: LegalDoc; onClose: () => void }) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="legal-overlay" onClick={onClose}>
      <div
        className="legal-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="legal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="legal-head">
          <div>
            <p className="eyebrow">Last updated {doc.updated}</p>
            <h2 id="legal-title">{doc.title}</h2>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close">
            <Icon name="close" />
          </button>
        </div>
        <div className="legal-body">
          <p>{doc.intro}</p>
          {doc.sections.map((section) => (
            <div key={section.heading}>
              <h3>{section.heading}</h3>
              {section.paragraphs?.map((text) => (
                <p key={text}>{text}</p>
              ))}
              {section.bullets && (
                <ul>
                  {section.bullets.map((text) => (
                    <li key={text}>{text}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
        <button className="primary-button" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}

function Signup({
  onBack,
  onRegister,
  onLogin,
}: {
  onBack: () => void;
  onRegister: (email: string, password: string) => Promise<void>;
  onLogin: () => void;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [legal, setLegal] = useState<"terms" | "privacy" | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError("");
    setBusy(true);
    try {
      await onRegister(
        String(form.get("email") ?? "").trim(),
        String(form.get("password") ?? ""),
      );
    } catch (err) {
      setError(api.messageOf(err));
      setBusy(false);
    }
  }

  return (
    <>
      <AuthHeader onBack={onBack} step="Step 1 of 2" />
      <main className="screen-content auth-content">
        <div className="title-block">
          <p className="eyebrow">Your account</p>
          <h1>Let’s get you started</h1>
          <p>Create a secure account to save your progress and results.</p>
        </div>
        <form onSubmit={submit} className="form-stack">
          <Field
            label="Email address"
            name="email"
            type="email"
            placeholder="you@example.com"
            icon="mail"
          />
          <Field
            label="Create password"
            name="password"
            type="password"
            placeholder="At least 12 characters"
            icon="lock"
            minLength={12}
          />
          <label className="consent-row">
            <input type="checkbox" required />
            <span>
              I agree to the{" "}
              <button type="button" onClick={() => setLegal("terms")}>
                Terms
              </button>{" "}
              and{" "}
              <button type="button" onClick={() => setLegal("privacy")}>
                Privacy Policy
              </button>
              .
            </span>
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Creating your account…" : "Continue"}
            <Icon name="arrow" size={19} />
          </button>
        </form>
        <p className="auth-switch">
          Already have an account?{" "}
          <button className="text-button" onClick={onLogin}>
            Sign in
          </button>
        </p>
      </main>
      {legal && (
        <LegalSheet doc={legalDocs[legal]} onClose={() => setLegal(null)} />
      )}
    </>
  );
}

function Profile({
  onBack,
  onContinue,
}: {
  onBack: () => void;
  onContinue: (name: string) => void;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onContinue(String(form.get("name") ?? "").trim());
  }

  return (
    <>
      <AuthHeader onBack={onBack} step="Step 2 of 2" />
      <main className="screen-content auth-content">
        <div className="profile-icon">
          <Icon name="user" size={25} />
        </div>
        <div className="title-block">
          <p className="eyebrow">Your profile</p>
          <h1>What should we call you?</h1>
          <p>A few details to make your experience feel more personal.</p>
        </div>
        <form onSubmit={submit} className="form-stack">
          <Field
            label="Preferred name"
            name="name"
            placeholder="e.g. Maya"
            icon="user"
          />
          <Field
            label="Date of birth"
            name="birthdate"
            type="date"
            icon="calendar"
          />
          <fieldset className="field">
            <legend className="field-label">Sex assigned at birth</legend>
            <div className="choice-grid">
              <label className="choice-card">
                <input type="radio" name="sex" value="female" required />
                <span>Female</span>
              </label>
              <label className="choice-card">
                <input type="radio" name="sex" value="intersex" />
                <span>Intersex</span>
              </label>
            </div>
          </fieldset>
          <button className="primary-button" type="submit">
            Start assessment
            <Icon name="arrow" size={19} />
          </button>
        </form>
        <p className="microcopy">
          This takes about 4 minutes. You can pause at any time.
        </p>
      </main>
    </>
  );
}

function ScoreSlider({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="slider-card">
      <div className="slider-heading">
        <div>
          <span className="field-label">{label}</span>
          <p>{hint}</p>
        </div>
        <output>{value}</output>
      </div>
      <input
        aria-label={label}
        type="range"
        min="0"
        max="10"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <div className="range-labels">
        <span>None</span>
        <span>Severe</span>
      </div>
    </div>
  );
}

function BinaryChoice({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <fieldset className="field">
      <legend className="field-label">{label}</legend>
      <div className="choice-grid">
        {["Yes", "No"].map((option) => (
          <label className="choice-card" key={option}>
            <input
              type="radio"
              name={label}
              required
              checked={value === option}
              onChange={() => onChange(option)}
            />
            <span>{option}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function Assessment({
  section,
  answers,
  setAnswers,
  onBack,
  onNext,
  error,
  busy,
  onMenuHome,
  onMenuResults,
  onMenuData,
  onMenuSignOut,
}: {
  section: number;
  answers: Answers;
  setAnswers: (answers: Answers) => void;
  onBack: () => void;
  onNext: () => void;
  error: string;
  busy: boolean;
  onMenuHome: () => void;
  onMenuResults: () => void;
  onMenuData: () => void;
  onMenuSignOut: () => void;
}) {
  const copy = assessmentSections[section];
  const update = <K extends keyof Answers>(key: K, value: Answers[K]) =>
    setAnswers({ ...answers, [key]: value });

  function submit(event: FormEvent) {
    event.preventDefault();
    onNext();
  }

  return (
    <>
      <header className="assessment-header">
        <button className="icon-button" onClick={onBack} aria-label="Go back">
          <Icon name="back" />
        </button>
        <div className="progress-track">
          <div
            className={`progress-fill progress-${section + 1}`}
            aria-label={`${section + 1} of 3 sections complete`}
          />
        </div>
        <span className="progress-label">{section + 1}/3</span>
        <AppMenu
          onHome={onMenuHome}
          onResults={onMenuResults}
          onData={onMenuData}
          onSignOut={onMenuSignOut}
        />
      </header>
      <main className="screen-content assessment-content">
        <div className="title-block">
          <p className="eyebrow">{copy.eyebrow}</p>
          <h1>{copy.title}</h1>
          <p>{copy.description}</p>
        </div>
        <form onSubmit={submit} className="form-stack assessment-form">
          {section === 0 && (
            <>
              <Field
                label="Current age"
                name="age"
                type="number"
                placeholder="e.g. 29"
                suffix="years"
                value={answers.age}
                onChange={(value) => update("age", value)}
                min="12"
                max="65"
              />
              <Field
                label="Body mass index (BMI)"
                name="bmi"
                type="number"
                placeholder="e.g. 22.4"
                value={answers.bmi}
                onChange={(value) => update("bmi", value)}
                min="12"
                max="70"
                step="any"
              />
              <div className="field-row">
                <Field
                  label="Cycle length"
                  name="cycle"
                  type="number"
                  placeholder="28"
                  suffix="days"
                  value={answers.cycleLength}
                  onChange={(value) => update("cycleLength", value)}
                  min="15"
                  max="90"
                />
                <Field
                  label="Age at first period"
                  name="menarche"
                  type="number"
                  placeholder="12"
                  suffix="years"
                  value={answers.menarcheAge}
                  onChange={(value) => update("menarcheAge", value)}
                  min="8"
                  max="20"
                />
              </div>
            </>
          )}
          {section === 1 && (
            <>
              <div className="scale-explainer">
                <span>0</span>
                <p>Use the 0–10 scale for each symptom</p>
                <span>10</span>
              </div>
              <ScoreSlider
                label="Period pain"
                hint="Dysmenorrhea"
                value={answers.dysmenorrhea}
                onChange={(value) => update("dysmenorrhea", value)}
              />
              <ScoreSlider
                label="Pelvic pain"
                hint="Outside of your period"
                value={answers.pelvicPain}
                onChange={(value) => update("pelvicPain", value)}
              />
              <ScoreSlider
                label="Pain during or after sex"
                hint="Dyspareunia"
                value={answers.dyspareunia}
                onChange={(value) => update("dyspareunia", value)}
              />
              <ScoreSlider
                label="Painful bowel movements"
                hint="Dyschezia"
                value={answers.dyschezia}
                onChange={(value) => update("dyschezia", value)}
              />
              <ScoreSlider
                label="Urinary symptoms"
                hint="Pain, urgency, or frequency"
                value={answers.urinary}
                onChange={(value) => update("urinary", value)}
              />
            </>
          )}
          {section === 2 && (
            <>
              <BinaryChoice
                label="Family history of endometriosis?"
                value={answers.familyHistory}
                onChange={(value) => update("familyHistory", value)}
              />
              <BinaryChoice
                label="Have you experienced infertility?"
                value={answers.infertility}
                onChange={(value) => update("infertility", value)}
              />
              <ScoreSlider
                label="Mental wellbeing"
                hint="How supported and emotionally well do you feel?"
                value={answers.mentalHealth}
                onChange={(value) => update("mentalHealth", value)}
              />
            </>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button
            className="primary-button sticky-action"
            type="submit"
            disabled={busy}
          >
            {section === 2
              ? busy
                ? "Calculating…"
                : "View my result"
              : "Continue"}
            {section === 2 ? (
              <Icon name="spark" size={19} />
            ) : (
              <Icon name="arrow" size={19} />
            )}
          </button>
        </form>
      </main>
    </>
  );
}

function Result({
  result,
  name,
  onRestart,
  onResult,

    onSignOut,
    onShowHistory,
    onShowData,
}: {
  result: api.Screening;
  name: string;
  onRestart: () => void;
  onResult: (result: api.Screening) => void;

    onShowHistory: () => void;
    onShowData: () => void;
    onSignOut: () => void;
}) {
  const [ca125, setCa125] = useState("");
  const [crp, setCrp] = useState("");
  const [labsError, setLabsError] = useState("");
  const [labsBusy, setLabsBusy] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [copied, setCopied] = useState(false);

  // Symptoms raised a flag but the lab values did not support it: the middle level.
  const level =
    result.recommendation === "low_risk"
      ? "Lower"
      : result.recommendation === "elevated_not_confirmed"
        ? "Moderate"
        : "Elevated";
  const message =
    level === "Elevated"
      ? "Your responses show several patterns that can be associated with endometriosis."
      : level === "Moderate"
        ? "Some of your responses match patterns that can be associated with endometriosis."
        : "Your responses show fewer patterns commonly associated with endometriosis.";
  const headline =
    result.tier2_probability_display ?? result.tier1_probability_display;
  const levelNote =
    level === "Lower"
      ? "Your symptoms did not raise a flag, so no blood test follow-up is suggested."
      : level === "Moderate"
        ? "Your symptoms were elevated, but your lab values did not support it. Keep monitoring and see a doctor if symptoms continue."
        : result.can_add_labs
          ? "Your symptoms were elevated. Adding blood test values below can help refine this result."
          : "Your symptoms and your lab values both point to elevated risk.";

  async function submitLabs(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLabsError("");
    setLabsBusy(true);
    try {
      const updated = await api.addLabs(result.id, {
        CA_125_Level: Number(ca125),
        CRP_Level: Number(crp),
      });
      onResult(updated);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setLabsError(api.messageOf(err));
    } finally {
      setLabsBusy(false);
    }
  }

  async function copySummary() {
    try {
      await navigator.clipboard.writeText(result.report_text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <main className="result-screen">
      <div className="result-topbar">
        <Brand compact />
                <div className="result-topbar-right">
          <span className="complete-pill">
            <Icon name="check" size={14} />
            Complete
          </span>
          <AppMenu
            onHome={onRestart}
            onResults={onShowHistory}
            onData={onShowData}
            onSignOut={onSignOut}
          />
        </div>
      </div>
      <div className="result-hero">
        <span className="result-kicker">
          {name ? `${name}’s assessment result` : "Your assessment result"}
        </span>
        <div className="score-ring">
          <div>
            <strong>{headline}</strong>
            <span>pattern match</span>
          </div>
        </div>
        <span className={`risk-pill risk-${level.toLowerCase()}`}>
          {level} indication
        </span>
        <p className="level-note">{levelNote}</p>
        {result.tier2_probability_display && (
          <p className="result-tiers">
            Symptoms alone: {result.tier1_probability_display} · With your lab
            values: {result.tier2_probability_display}
          </p>
        )}
        {level !== "Elevated" && (
          <p className="level-caution">
            A low score on this prototype is not a reassurance about your
            health. If your symptoms continue or worry you, please see a doctor.
          </p>
        )}
        <h1>{message}</h1>
        <p>
          This result is a screening insight, not a diagnosis. Only a qualified
          clinician can diagnose endometriosis.
        </p>
      </div>
      {result.can_add_labs && (
        <section className="labs-card">
          <p className="eyebrow">Optional follow-up</p>
          <h2>Refine your result with blood markers</h2>
          <p>
            If you have CA-125 and CRP results, for example from a mail-in
            finger-prick kit or a clinic, add both here to refine your estimate.
          </p>
          <form onSubmit={submitLabs} className="form-stack">
            <Field
              label="CA-125 level"
              name="ca125"
              type="number"
              placeholder="e.g. 24"
              suffix="U/mL"
              value={ca125}
              onChange={setCa125}
              min="0"
              max="5000"
              step="any"
            />
            <Field
              label="CRP level"
              name="crp"
              type="number"
              placeholder="e.g. 3.1"
              suffix="mg/L"
              value={crp}
              onChange={setCrp}
              min="0"
              max="500"
              step="any"
            />
            {labsError && (
              <p className="form-error" role="alert">
                {labsError}
              </p>
            )}
            <button
              className="primary-button"
              type="submit"
              disabled={labsBusy}
            >
              {labsBusy ? "Updating…" : "Update my result"}
              <Icon name="arrow" size={19} />
            </button>
          </form>
        </section>
      )}
      <section className="next-steps">
        <p className="eyebrow">Recommended next step</p>
        <h2>Talk with a healthcare professional</h2>
        <p>{result.next_step}</p>
        <p>
          Bring your result and symptom history to a GP or gynecologist. It can
          help you start a more informed conversation.
        </p>
        <button
          className="primary-button"
          onClick={() => setShowSummary(!showSummary)}
        >
          {showSummary ? "Hide doctor summary" : "Prepare doctor summary"}
          <Icon name="arrow" size={19} />
        </button>
      </section>
      {showSummary && (
        <section className="summary-card">
          <p className="eyebrow">Doctor summary</p>
          <div className="summary-text">{result.report_text}</div>
          <div className="summary-actions">
            <button className="secondary-button" onClick={() => window.print()}>
              Print
            </button>
            <button className="secondary-button" onClick={copySummary}>
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </section>
      )}
      <section className="result-actions">
        <p className="saved-note">
          <Icon name="check" size={14} />
          Saved to your account
        </p>
        <button className="text-button" onClick={onRestart}>
          Retake assessment
        </button>
      </section>
      {result.prototype_notice && (
        <p className="result-disclaimer">{result.prototype_notice}</p>
      )}
      <p className="result-disclaimer">
        If you have severe or sudden pain, heavy bleeding, fainting, or feel
        acutely unwell, seek urgent medical care.
      </p>
    </main>
  );
}

function levelOf(recommendation: api.Recommendation): string {
  if (recommendation === "low_risk") return "Lower";
  if (recommendation === "elevated_not_confirmed") return "Moderate";
  return "Elevated";
}

function History({
  onBack,
  onOpen,
  onMenuHome,
  onMenuResults,
  onMenuData,
  onSignOut,
}: {
  onBack: () => void;
  onOpen: (id: string) => Promise<void>;
  onMenuHome: () => void;
  onMenuResults: () => void;
  onMenuData: () => void;
  onSignOut: () => void;
}) {
  const [items, setItems] = useState<api.ScreeningSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [openingId, setOpeningId] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .listScreenings(20, 0)
      .then((data) => {
        if (cancelled) return;
        setItems(data.items);
        setTotal(data.total);
      })
      .catch((err) => {
        if (!cancelled) setError(api.messageOf(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function loadMore() {
    setLoadingMore(true);
    setError("");
    try {
      const data = await api.listScreenings(20, items.length);
      setItems([...items, ...data.items]);
      setTotal(data.total);
    } catch (err) {
      setError(api.messageOf(err));
    } finally {
      setLoadingMore(false);
    }
  }

  async function open(id: string) {
    setOpeningId(id);
    setError("");
    try {
      await onOpen(id);
    } catch (err) {
      setError(api.messageOf(err));
      setOpeningId("");
    }
  }

  return (
    <>
      <header className="topbar">
        <button className="icon-button" onClick={onBack} aria-label="Go back">
          <Icon name="back" />
        </button>
        <Brand compact />
        <AppMenu
          onHome={onMenuHome}
          onResults={onMenuResults}
          onData={onMenuData}
          onSignOut={onSignOut}
        />
      </header>
      <main className="screen-content">
        <div className="title-block">
          <p className="eyebrow">Saved to your account</p>
          <h1>My results</h1>
          <p>Tap a result to see it again.</p>
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {loading ? (
          <p className="microcopy">Loading your results…</p>
        ) : items.length === 0 && !error ? (
          <div className="history-empty">
            You have no saved results yet. Once you finish an assessment, it
            will appear here.
          </div>
        ) : (
          <div className="history-list">
            {items.map((item) => {
              const level = levelOf(item.recommendation);
              return (
                <button
                  key={item.id}
                  className="history-card"
                  onClick={() => void open(item.id)}
                  disabled={openingId !== ""}
                >
                  <span>
                    <span className="history-date">
                      {new Date(item.created_at).toLocaleDateString(undefined, {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                    <span className={`risk-pill risk-${level.toLowerCase()}`}>
                      {openingId === item.id ? "Opening…" : `${level} indication`}
                    </span>
                  </span>
                  <strong className="history-score">
                    {item.tier2_probability_display ??
                      item.tier1_probability_display}
                  </strong>
                </button>
              );
            })}
          </div>
        )}
        {!loading && items.length < total && (
          <div className="history-more">
            <button
              className="secondary-button"
              onClick={() => void loadMore()}
              disabled={loadingMore}
            >
              {loadingMore ? "Loading…" : "Show more"}
            </button>
          </div>
        )}
      </main>
    </>
  );
}

function MyData({
  onBack,
  onMenuHome,
  onMenuResults,
  onMenuData,
  onSignOut,
  onDeleted,
}: {
  onBack: () => void;
  onMenuHome: () => void;
  onMenuResults: () => void;
  onMenuData: () => void;
  onSignOut: () => void;
  onDeleted: () => void;
}) {
  const [downloading, setDownloading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [password, setPassword] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  async function download() {
    setDownloading(true);
    setError("");
    setNotice("");
    try {
      const data = await api.exportAccount();
      const text =
        typeof data === "string" ? data : JSON.stringify(data, null, 2);
      const blob = new Blob([text], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "enara-my-data.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setNotice("Your data was saved as enara-my-data.json.");
    } catch (err) {
      setError(api.messageOf(err));
    } finally {
      setDownloading(false);
    }
  }

  async function deleteEverything(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDeleting(true);
    setDeleteError("");
    try {
      await api.deleteAccount(password);
      onDeleted();
    } catch (err) {
      setDeleteError(api.messageOf(err));
      setDeleting(false);
    }
  }

  return (
    <>
      <header className="topbar">
        <button className="icon-button" onClick={onBack} aria-label="Go back">
          <Icon name="back" />
        </button>
        <Brand compact />
        <AppMenu
          onHome={onMenuHome}
          onResults={onMenuResults}
          onData={onMenuData}
          onSignOut={onSignOut}
        />
      </header>
      <main className="screen-content">
        <div className="title-block">
          <p className="eyebrow">Your privacy</p>
          <h1>My data</h1>
          <p>You are in control of what Enara keeps about you.</p>
        </div>
        <section className="data-card">
          <h2>Download my data</h2>
          <p>
            Save a copy of your account details and saved results as a file
            you can keep.
          </p>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          {notice && (
            <p className="form-notice" role="status">
              {notice}
            </p>
          )}
          <button
            className="secondary-button"
            onClick={() => void download()}
            disabled={downloading}
          >
            {downloading ? "Preparing…" : "Download my data"}
          </button>
        </section>
        <section className="data-card data-card-danger">
          <h2>Delete my account</h2>
          <p>
            This permanently deletes your account and all your saved results.
            It cannot be undone.
          </p>
          {!confirming ? (
            <button
              className="secondary-button"
              onClick={() => setConfirming(true)}
            >
              Delete my account…
            </button>
          ) : (
            <form onSubmit={deleteEverything} className="form-stack">
              <Field
                label="Enter your password to confirm"
                name="confirm-password"
                type="password"
                placeholder="Your password"
                icon="lock"
                value={password}
                onChange={setPassword}
              />
              {deleteError && (
                <p className="form-error" role="alert">
                  {deleteError}
                </p>
              )}
              <button
                className="danger-button"
                type="submit"
                disabled={deleting}
              >
                {deleting ? "Deleting…" : "Yes, delete everything"}
              </button>
              <button
                type="button"
                className="text-button"
                onClick={() => {
                  setConfirming(false);
                  setPassword("");
                  setDeleteError("");
                }}
              >
                Cancel
              </button>
            </form>
          )}
        </section>
      </main>
    </>
  );
}

function nameKey(email: string) {
  return `enara-name:${email.trim().toLowerCase()}`;
}

function loadName(email: string): string {
  try {
    return window.localStorage.getItem(nameKey(email)) ?? "";
  } catch {
    return "";
  }
}

function saveName(email: string, name: string) {
  try {
    window.localStorage.setItem(nameKey(email), name);
  } catch {
    // storage unavailable: the name just will not be remembered
  }
}

function removeName(email: string) {
  try {
    window.localStorage.removeItem(nameKey(email));
  } catch {
    // nothing to remove
  }
}

function toPayload(answers: Answers): api.SymptomPayload {
  return {
    Age: Number(answers.age),
    BMI: Number(answers.bmi),
    Cycle_Length: Number(answers.cycleLength),
    Age_of_Menarche: Number(answers.menarcheAge),
    Dysmenorrhea_Score: answers.dysmenorrhea,
    Pelvic_Pain_Score: answers.pelvicPain,
    Dyspareunia_Score: answers.dyspareunia,
    Dyschezia_Score: answers.dyschezia,
    Urinary_Symptoms_Score: answers.urinary,
    Mental_Health_Score: answers.mentalHealth,
    Family_History: answers.familyHistory === "Yes",
    Infertility_Status: answers.infertility === "Yes",
  };
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("welcome");
  const [section, setSection] = useState(0);
  const [answers, setAnswers] = useState<Answers>(initialAnswers);
  const [name, setName] = useState("");
  const [result, setResult] = useState<api.Screening | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [assessmentError, setAssessmentError] = useState("");
  const [loginNotice, setLoginNotice] = useState("");
  const [cameFromProfile, setCameFromProfile] = useState(false);
  const [userEmail, setUserEmail] = useState("");

  useEffect(() => {
    api.setUnauthorizedHandler(() => {
      setResult(null);
      setLoginNotice("Your session has ended. Please sign in again.");
      setScreen("login");
    });
    return () => api.setUnauthorizedHandler(null);
  }, []);

  async function signIn(email: string, password: string) {
    await api.login(email, password);
    setLoginNotice("");
    setCameFromProfile(false);setScreen("assessment");    setUserEmail(email);
    setName(loadName(email));
  }

  async function createAccount(email: string, password: string) {
    await api.register(email, password);
    await api.login(email, password);
    setLoginNotice("");
    setCameFromProfile(true);setScreen("profile");    setUserEmail(email);
    setName("");
  }

  async function submitAssessment() {
    setSubmitting(true);
    setAssessmentError("");
    try {
      const screening = await api.createScreening(toPayload(answers));
      setResult(screening);
      setScreen("result");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setAssessmentError(api.messageOf(err));
    } finally {
      setSubmitting(false);
    }
  }

      async function openSaved(id: string) {
    const saved = await api.getScreening(id);
    setResult(saved);
    setScreen("result");
    window.scrollTo({ top: 0 });
  }
  
    function accountDeleted() {
    removeName(userEmail);
    setUserEmail("");
    api.signOut();
    setAnswers(initialAnswers);
    setSection(0);
    setResult(null);
    setName("");
    setAssessmentError("");
    setLoginNotice("Your account and saved results have been deleted.");
    setScreen("login");
  }
  
    function hasTypedAnswers() {
    return (
      answers.age !== "" ||
      answers.bmi !== "" ||
      answers.cycleLength !== "" ||
      answers.menarcheAge !== "" ||
      answers.familyHistory !== "" ||
      answers.infertility !== ""
    );
  }

  function confirmLeave(action: () => void) {
    if (
      !hasTypedAnswers() ||
      window.confirm("Leave this assessment? Your answers will be lost.")
    ) {
      action();
    }
  }
  
  function signOutUser() {
    setUserEmail("");
    api.signOut();
    setAnswers(initialAnswers);
    setSection(0);
    setResult(null);
    setName("");
    setAssessmentError("");
    setLoginNotice("You have been signed out.");
    setScreen("login");
  }
  
  function reset() {
    setAnswers(initialAnswers);
    setSection(0);
    setResult(null);
    setAssessmentError("");
    setScreen("assessment");
  }

  return (
    <div className="app-shell">
      <div className="phone-frame">
        {screen === "welcome" && (
          <Welcome
            onLogin={() => setScreen("login")}
            onSignup={() => setScreen("signup")}
          />
        )}
        {screen === "login" && (
          <Login
            onBack={() => setScreen("welcome")}
            onSignIn={signIn}
            onSignup={() => setScreen("signup")}
            notice={loginNotice}
          />
        )}
        {screen === "signup" && (
          <Signup
            onBack={() => setScreen("welcome")}
            onRegister={createAccount}
            onLogin={() => setScreen("login")}
          />
        )}
        {screen === "profile" && (
          <Profile
            onBack={() => setScreen("signup")}
            onContinue={(preferredName) => {
              setName(preferredName);
              saveName(userEmail, preferredName);
              setScreen("assessment");
            }}
          />
        )}
        {screen === "assessment" && (
          <Assessment
            section={section}
            answers={answers}
            setAnswers={setAnswers}
            error={assessmentError}
            busy={submitting}
            onBack={() => {
              if (section > 0) setSection(section - 1);
                            else if (cameFromProfile) setScreen("profile");
              else if (
                window.confirm(
                  "Go back? You will be signed out and your answers will be lost.",
                )
              )
                signOutUser();
            }}
            onNext={() => {
              if (section < 2) {
                setSection(section + 1);
                window.scrollTo({ top: 0, behavior: "smooth" });
              } else {
                void submitAssessment();
              }
            }}
            onMenuHome={() => confirmLeave(reset)}
            onMenuResults={() => confirmLeave(() => setScreen("history"))}
            onMenuData={() => confirmLeave(() => setScreen("mydata"))}
            onMenuSignOut={() => confirmLeave(signOutUser)}
          />
        )}
                        {screen === "mydata" && (
          <MyData
            onBack={() => setScreen(result ? "result" : "assessment")}
            onMenuHome={reset}
            onMenuResults={() => setScreen("history")}
            onMenuData={() => setScreen("mydata")}
            onSignOut={signOutUser}
            onDeleted={accountDeleted}
          />
        )}{screen === "history" && (
          <History
            onBack={() => setScreen(result ? "result" : "assessment")}
            onOpen={openSaved}
            onMenuHome={reset}
            onMenuResults={() => setScreen("history")}
            onMenuData={() => setScreen("mydata")}
            onSignOut={signOutUser}
          />
        )}
        {screen === "result" && result && (
          <Result
            result={result}
            name={name}
            onRestart={reset}
            onResult={setResult}
                        onSignOut={signOutUser}
                        onShowHistory={() => setScreen("history")}
                        onShowData={() => setScreen("mydata")}
          />
        )}
      </div>
    </div>
  );
}
