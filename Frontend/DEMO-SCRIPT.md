# Enara demo script (about 5 minutes)

## Before you start (do this beforehand)
- Docker Desktop is running; http://127.0.0.1:8000/health shows "status":"ok"
- Frontend is running: http://localhost:3000 shows the Welcome screen
- You are signed out.
- Have a FRESH email (for example demo04@example.com) and a 12+ character
  password ready. Write the password down: there is no password reset.
- Use a fresh account for the demo. A fresh account shows the name being set
  during sign-up. Older accounts created before the name feature (for example
  testuser01) have no saved name and show "Your assessment result".
- Browser zoom at 100%, notifications off.

## The walk-through
1. **Welcome.** "Enara is a private, guided symptom screening for endometriosis.
   It is a research prototype, not a diagnosis."
2. **Create an account.** Open the Terms and Privacy Policy links. Say: "Consent
   is recorded with a version, and the password needs 12+ characters." Click the
   eye icon to show the password: "People can check what they typed, which
   matters because there is no password reset."
3. **Profile.** "The name only appears in the heading of the result screen, and
   is remembered in this browser only. Date of birth and sex are not sent to the
   server."
4. **Assessment, parts 1 to 3.** Use Back once to show answers are kept. Open the
   menu to show navigation, and show the "Leave this assessment?" warning. Set
   the pain sliders high (7 to 8) so the result is Elevated.
5. **Result.** Point out the name in the heading, the level, the percentage, the
   plain-words explanation, and the "not a diagnosis" wording.
6. **Tier 2.** "Blood values are only offered when Tier 1 flags elevated."
   Enter CA-125 = 60 and CRP = 8, click Update. Show "Symptoms alone" versus
   "With your lab values".
7. **Doctor summary.** Click it, then Copy. "This is the report a person can
   bring to a GP."
8. **My results.** Open the menu, then My results, and open a past result.
9. **My data.** Download the file and open it. "Everything the service stores
   about you, in one file." Mention that Delete account is permanent and asks
   for the password. Do NOT delete the demo account live.
10. **Sign out.** The Welcome screen should be clean.

## Likely questions and answers

**Is this a diagnosis?**
No. It is a screening prototype. Only a clinician can diagnose endometriosis.
Every result says so.

**What data trained the models?**
A synthetic dataset. The app and the health endpoint state the models have not
been validated on real patients (model_validated is false). The next step would
be validation on real clinical data with ethics approval.

**Why two tiers?**
Tier 1 uses 12 symptom answers anyone can give at home. Tier 2 adds CA-125 and
CRP blood markers and is allowed only if Tier 1 flagged elevated, so people are
not pushed toward tests they do not need.

**How is privacy handled?**
Consent is recorded with a version. Passwords are never returned. Users can
download everything stored (My data) and permanently delete their account and
results. The login token is kept in memory only, and sessions last 30 minutes.
Date of birth and sex are never sent to the server.

**Why does the result sometimes say Moderate, even with a tiny percentage?**
Symptoms were elevated, but the blood values did not support it. The percentage
shown after labs is the second-tier estimate, so it can fall very low (for
example under 1%). The app labels this Moderate rather than Lower because the
symptoms were flagged.

**What happens if the Tier 1 score is low?**
No blood test is suggested, but the app says a low score is not a reassurance
and to see a doctor if symptoms continue.

**Why is the name sometimes missing?**
The name is saved in the browser only, per account, so a different device or a
cleared browser will not have it. This keeps personal details off the server.

**Forgot password does nothing. Why?**
Password reset needs email delivery and reset tokens, which are outside the scope
of this prototype. It is listed as future work.

**How did you test it?**
157 automated backend tests and an 83-check smoke test, both passing, plus a
manual walk-through of the full user journey.

**What would you do next?**
Validate on real data, add password reset, add email delivery for the blood-test
kit flow, and have clinicians review the wording.