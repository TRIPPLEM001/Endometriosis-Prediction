// The text of Enara's Terms of Use and Privacy Policy.
// BEFORE SHARING THE APP: replace the two placeholders below with real details.
export const OWNER = "[your name or institution]";
export const CONTACT = "[your contact email]";

export type LegalSection = {
  heading: string;
  paragraphs?: string[];
  bullets?: string[];
};

export type LegalDoc = {
  title: string;
  updated: string;
  intro: string;
  sections: LegalSection[];
};

export const legalDocs: Record<"terms" | "privacy", LegalDoc> = {
  terms: {
    title: "Terms of Use",
    updated: "November 2026",
    intro:
      "Enara is a student research prototype run by " +
      OWNER +
      ". By creating an account you agree to these terms. They are written in plain language so you know what to expect.",
    sections: [
      {
        heading: "What Enara is",
        paragraphs: [
          "Enara is a screening aid. It uses a machine-learning model to estimate how closely your answers match patterns linked to endometriosis. It is not a medical device and it does not diagnose anything.",
          "The models were trained on a synthetic (made-up) dataset and have not been tested on real patients. A score from Enara, high or low, says nothing certain about your health.",
        ],
      },
      {
        heading: "Not medical advice",
        paragraphs: [
          "Only a qualified clinician can diagnose endometriosis. Please talk to a doctor if you have symptoms that worry you, whatever Enara shows.",
          "If you have severe or sudden pain, heavy bleeding, fainting, or feel acutely unwell, seek urgent medical care right away. Do not wait for or rely on this app.",
        ],
      },
      {
        heading: "Your account",
        bullets: [
          "Use your own email address and give answers that are as accurate as you can.",
          "Choose a password of at least 12 characters and keep it private.",
          "For your safety you are signed out automatically after 30 minutes.",
        ],
      },
      {
        heading: "Using Enara fairly",
        bullets: [
          "Only enter information about yourself.",
          "Do not try to access other people’s accounts or to disrupt the service.",
        ],
      },
      {
        heading: "No guarantees",
        paragraphs: [
          "Enara is a prototype. It may change, contain mistakes, or be unavailable without notice, and results may be wrong. We cannot accept responsibility for decisions made only on the basis of its results.",
        ],
      },
      {
        heading: "Leaving Enara",
        paragraphs: [
          "You can delete individual results, all your results, or your whole account at any time. You can also download a copy of your data first.",
        ],
      },
      {
        heading: "Changes and contact",
        paragraphs: [
          "If these terms change in a meaningful way, we will ask you to agree again. Questions? Contact " +
            CONTACT +
            ".",
        ],
      },
    ],
  },
  privacy: {
    title: "Privacy Policy",
    updated: "November 2026",
    intro:
      "Your health information is sensitive. This page explains what Enara keeps, why, and how you stay in control. The service is run by " +
      OWNER +
      ".",
    sections: [
      {
        heading: "What we keep",
        bullets: [
          "Your email address.",
          "Your password, stored only as a scrambled one-way “hash”. Nobody, including us, can read it.",
          "Your symptom answers and, if you add them, your CA-125 and CRP blood values.",
          "Your results, the factors behind them, and the doctor summary generated for each one.",
          "When you agreed to these terms, and which version you agreed to.",
        ],
      },
      {
        heading: "What we do not keep",
        paragraphs: [
          "The name you type on the profile screen is only used on your screen while you use the app. Your date of birth and sex assigned at birth are not collected or stored.",
          "Enara does not use advertising or analytics trackers, and it does not store anything in cookies. Your login is held only in the open page and ends when you close or refresh it.",
        ],
      },
      {
        heading: "Why we keep it",
        paragraphs: [
          "To calculate your results, show them back to you, and prepare a summary you can share with a doctor. We do not sell your information and we do not share it with other companies for their own purposes.",
          "One exception: Enara’s fonts are loaded from Google Fonts, so your browser contacts Google when the page opens.",
        ],
      },
      {
        heading: "Who can see it",
        paragraphs: [
          "Your results are linked to your account and the service only shows them to you. The people who run this prototype can technically reach the database it is stored in, and will only do so to maintain or test the service.",
        ],
      },
      {
        heading: "How safe is it?",
        paragraphs: [
          "This is a prototype, not a clinical service. It does not yet have every safeguard a real health service needs, such as encrypted connections everywhere, backups, and independent security review. While it is in this stage, please prefer made-up or low-stakes information.",
        ],
      },
      {
        heading: "Your choices",
        bullets: [
          "Download a copy of everything we hold about you.",
          "Delete one result, all your results, or your whole account. Deleting your account removes your data and withdraws your consent.",
        ],
      },
      {
        heading: "How long we keep it",
        paragraphs: [
          "Until you delete it. There is no automatic clean-up yet.",
        ],
      },
      {
        heading: "Changes and contact",
        paragraphs: [
          "If this policy changes in a meaningful way, we will ask you to agree again. Questions or requests? Contact " +
            CONTACT +
            ".",
        ],
      },
    ],
  },
};
