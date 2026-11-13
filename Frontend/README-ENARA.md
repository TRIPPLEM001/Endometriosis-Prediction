# Enara: frontend

Enara is the user interface for the endometriosis screening research prototype.
It is a React 19 + TypeScript + Vite + Tailwind app that talks to the FastAPI
backend in the `backend` folder.

> **Research prototype, not a diagnosis.** The models behind Enara were trained
> on a synthetic dataset and have not been validated on real patients. Results
> are a prompt to talk to a doctor, not information about anyone's health status.

## What it does

1. Create an account (with consent) or sign in.
2. Answer 12 symptom questions (Tier 1).
3. See a result: Lower, Moderate or Elevated indication, with a plain-words
   explanation and a recommended next step.
4. If Tier 1 is elevated, optionally add CA-125 and CRP blood values (Tier 2)
   to refine the result.
5. Prepare a doctor summary (copy or print).
6. Revisit saved results under **My results**.
7. Download or permanently delete your data under **My data**.

## Run it

You need Node.js and the backend running first.

1. Start the backend (Docker Desktop must be running):
   `cd backend` then `docker compose up`
   Check http://127.0.0.1:8000/health shows `"status":"ok"`.
2. Start the frontend:
   `cd Frontend`, then `npm install` (first time only), then `npm run dev`
3. Open http://localhost:3000

The backend only accepts requests from `http://localhost:3000`, so keep that port.
To point the app at a different backend, set `VITE_API_URL`.

## Project layout

- `src/App.tsx`: all screens (welcome, sign in, sign up, profile, assessment,
  result, My results, My data) and the menu
- `src/api.ts`: every call to the backend; the login token is kept in memory only
- `src/legal.ts`: Terms of Use and Privacy Policy text
- `src/index.css`: all styling (plum, rose and cream palette; DM Sans and Fraunces)

## Notes and limits

- Sessions last 30 minutes, then the app returns to sign in.
- Password boxes have a show/hide (eye) button, so people can check what they
  typed. This matters because there is no password reset.
- Closing or refreshing the page signs you out (the token is not stored).
- "Forgot password?" is inactive: the backend has no password reset.
- Profile details (name, date of birth, sex) are never sent to the backend. Only
  the preferred name is kept, in this browser's local storage under the account's
  email, and it appears in the heading of the result screen. It is removed when
  the account is deleted. A different device or a cleared browser will not have it.
- Deleting an account removes the account and all saved results permanently.
