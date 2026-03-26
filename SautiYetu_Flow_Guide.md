# SautiYetu — System Flow Guide
**How everything connects, without the code**

---

## What is SautiYetu?

SautiYetu ("Our Voice") is a civic engagement platform for Kenyan citizens. It lets ordinary people — including those without smartphones — ask questions about their rights, track government activity, report irregularities, and sign petitions. All through SMS, USSD, voice calls, or a web dashboard.

---

## The Big Picture

Every interaction in SautiYetu follows the same general path:

```
Citizen acts
    ↓
Africa's Talking receives it
    ↓
FastAPI backend processes it
    ↓
Gemini (AI) thinks about it
    ↓
Response goes back to the citizen
    ↓
Interaction is logged to BigQuery
    ↓
Dashboard reflects the data
```

The backend is the brain. Africa's Talking is the ears and mouth. Gemini is the intelligence. BigQuery is the memory. The React dashboard is the face.

---

## Feature 1 — SMS Civic Education

### Who uses it
Any Kenyan with a basic phone. No internet needed.

### The flow
1. A citizen texts a question to the SautiYetu shortcode
   - Example: *"What are my voting rights?"*
2. Africa's Talking receives the SMS and immediately forwards it to the SautiYetu backend
3. The backend checks — does the message start with `FACT:`?
   - If yes → send to the Fact-Checker (see Feature 3)
   - If no → send to Gemini for a civic education answer
4. Gemini reads the question with full knowledge of the Kenyan Constitution, electoral laws, and government structure
5. Gemini returns an answer capped at 160 characters (one SMS)
6. The backend sends the answer back through Africa's Talking to the citizen's phone
7. The interaction (question + answer) is logged to BigQuery

### What makes it smart
Gemini is given a system prompt that tells it to always respond in the citizen's language (English or Swahili), cite the relevant constitutional article, and keep answers simple. It is grounded in actual Kenyan legal documents via Vertex AI Search — so it doesn't guess.

---

## Feature 2 — USSD Menu Flow

### Who uses it
Any Kenyan with any phone — USSD works even on the most basic handsets with no data.

### The flow
1. Citizen dials `*384#`
2. Africa's Talking opens a session and sends the dial event to the backend
3. The backend returns a menu — the citizen sees it on their screen:
   ```
   1. Civic Education
   2. Track a Bill
   3. Report Irregularity
   4. Sign a Petition
   ```
4. Citizen presses a number key
5. Africa's Talking sends that choice to the backend
6. Backend returns the next level of the menu or a final answer
7. This continues until the citizen reaches a leaf — a final answer or completed action
8. Every action is logged to BigQuery

### Key concept — CON vs END
Every USSD response from the backend starts with either:
- `CON` — the conversation continues, show another menu
- `END` — the conversation is over, show a final message and close the session

### Example journey
```
Citizen dials *384#
→ Sees main menu → presses 1 (Civic Education)
→ Sees sub-menu → presses 3 (Ask a Question)
→ Types "Who is my ward representative?"
→ Gemini answers → session ends with "END [answer]"
```

---

## Feature 3 — AI Fact-Checking

### Who uses it
Any citizen who wants to verify a political claim — via SMS.

### The flow
1. Citizen texts `FACT:` followed by the claim
   - Example: *"FACT: The president serves a 4-year term in Kenya"*
2. Africa's Talking forwards it to the backend
3. The backend detects the `FACT:` prefix and routes to the fact-checker
4. The fact-checker sends the claim to Gemini with a special prompt
5. Gemini returns a structured verdict:
   - **VERDICT:** TRUE / FALSE / MISLEADING / UNVERIFIED
   - **REASON:** One-sentence explanation
   - **SOURCE:** Relevant law or article
6. Backend sends the verdict back as an SMS
7. Interaction logged to BigQuery

### Example
```
Citizen sends: "FACT: The president serves a 4-year term in Kenya"

SautiYetu replies:
"VERDICT: MISLEADING
REASON: The president serves a 5-year term, renewable once.
SOURCE: Article 142, Constitution of Kenya 2010"
```

---

## Feature 4 — Voice IVR Agent

### Who uses it
Citizens who prefer speaking over typing — especially in rural areas or for those with low literacy.

### The flow
1. Citizen calls the SautiYetu phone number
2. Africa's Talking answers the call and sends the call event to the backend
3. The backend responds with a voice XML script — Africa's Talking reads this to the caller
4. Citizen hears: *"Welcome to SautiYetu. Ask your civic question after the beep."*
5. Citizen speaks their question
6. Africa's Talking records the audio and sends the recording URL to the backend
7. The backend processes the recording using Gemini's audio capabilities
8. Gemini transcribes, understands, and generates an answer
9. The answer is read back to the citizen via Africa's Talking text-to-speech
10. The interaction is logged to BigQuery

### Why this matters
Voice reaches citizens who cannot read or type. It also supports local languages — Swahili, Kikuyu, Luo — making SautiYetu genuinely inclusive.

---

## Feature 5 — BigQuery Logging and Dashboard Data

### What it is
BigQuery is Google's data warehouse. Every single interaction on SautiYetu — every SMS, USSD session, voice call, petition signature — gets written to BigQuery in real time.

### What gets stored
For every interaction:
- The citizen's phone number (anonymised in production)
- The channel used (SMS, USSD, voice, petition, report)
- What the citizen said or asked
- What SautiYetu responded
- The timestamp
- A sentiment score (positive / neutral / negative)

### How the dashboard uses it
The React dashboard queries BigQuery to show:
- Total interactions by channel (bar chart)
- Engagement trends over time (line chart)
- Geographic distribution across counties (map)
- Recent interactions feed (live table)
- Sentiment hotspots — where citizens are most dissatisfied

This is what government officials and accountability monitors see.

---

## Feature 6 — Legislative Tracker

### Who uses it
Citizens and researchers who want to follow what is happening in Parliament.

### The flow
1. Citizen or official visits the SautiYetu web dashboard
2. They open the Legislative Tracker page
3. The frontend requests the list of bills from the backend
4. The backend returns bills with their current status:
   - First Reading → Second Reading → Committee Stage → Third Reading → Signed into Law
5. Citizen clicks on a bill
6. The backend asks Gemini to summarise that bill in plain language
7. The citizen sees the bill status + an AI-generated plain-language summary
8. They can also text `BILL [number]` via SMS to get the same information on their basic phone

### Why it matters
Most Kenyans have no visibility into what Parliament is debating on their behalf. This makes it accessible to everyone.

---

## Feature 7 — Citizen Petitions

### Who uses it
Any citizen who wants to mobilise support for a civic cause.

### The flow — Web
1. Citizen visits the Petitions page on the dashboard
2. They see a list of active petitions with current signature counts
3. They enter their phone number and click "Sign Petition"
4. The backend records the signature in BigQuery
5. The signature count updates in real time on the page

### The flow — USSD
1. Citizen dials `*384#` → selects option 4 (Sign a Petition)
2. They see the list of active petitions
3. They press the number of the petition they want to sign
4. The backend records the signature with their phone number
5. They receive a confirmation message

### Why phone number matters
Using the phone number as identity prevents duplicate signatures and allows the petition to be verified as coming from real, unique Kenyan phone numbers — making it credible when presented to officials.

---

## Feature 8 — Vertex AI Search (RAG Grounding)

### What it is
RAG stands for Retrieval-Augmented Generation. Instead of Gemini answering from general training data (which could be outdated or wrong), it first searches a database of real Kenyan legal documents, then uses what it finds to answer.

### What documents are uploaded
- The Constitution of Kenya 2010
- The Elections Act
- The Public Finance Management Act
- County Government Act
- Any other relevant Kenyan statutes

### How it works in the flow
1. A citizen asks a question via SMS, USSD, or voice
2. Before sending to Gemini, the backend searches Vertex AI Search with the same question
3. Vertex AI Search returns the most relevant passages from the uploaded documents
4. The backend passes both the question AND the relevant legal passages to Gemini
5. Gemini answers using that specific context — not guesswork
6. The answer is grounded in actual Kenyan law

### Why this matters
Without grounding, Gemini might give a generic answer about African constitutions. With grounding, it gives the exact Article from the Kenyan Constitution 2010. This is the difference between a useful tool and a dangerous one.

---

## How the Backend Ties Everything Together

The FastAPI backend is the central hub. Think of it as a post office:

- It has a different address (route) for each type of incoming request
- `/sms` receives SMS messages from Africa's Talking
- `/ussd` receives USSD session data from Africa's Talking
- `/voice` receives voice call events from Africa's Talking
- `/api/bills` serves bill data to the React frontend
- `/api/petitions` serves and receives petition data
- `/api/stats` serves BigQuery analytics to the dashboard

Every request that comes in gets processed, sent to Gemini if needed, logged to BigQuery, and a response sent back — all in under two seconds.

---

## How the Frontend Connects

The React web dashboard is a separate application that communicates with the backend exclusively through the API. It never touches Africa's Talking or Gemini directly.

```
React Dashboard
    ↓ HTTP requests to /api/...
FastAPI Backend
    ↓ queries
BigQuery (for analytics)
    ↓ reads
Gemini (for bill summaries)
```

The three pages and what they show:

**Dashboard (Home)**
The accountability overview. Charts showing citizen engagement by channel, recent interactions feed, and sentiment trends. This is what a government official or journalist would open first.

**Legislative Tracker**
A browsable list of current bills in Parliament with their stage and an AI-generated plain-language summary of each.

**Petitions**
Active citizen petitions with real-time signature counts. Citizens can sign directly from the web or via USSD.

---

## Deployment Flow

Once everything is built and tested locally, the backend is deployed to Google Cloud Run — Google's serverless container platform.

```
Developer pushes code to GitHub
    ↓
GitHub Actions runs automated tests
    ↓
If tests pass → builds a Docker container
    ↓
Container is deployed to Cloud Run (africa-south1 region)
    ↓
Cloud Run gives a public HTTPS URL
    ↓
That URL is set as the callback in Africa's Talking dashboard
    ↓
Citizens can now interact with SautiYetu from anywhere
```

Cloud Run automatically scales up when many citizens are interacting and scales down to zero when quiet — so the team only pays for actual usage.

---

## Data Flow Summary

```
CITIZEN
  │
  ├── SMS/USSD/Voice ──→ Africa's Talking ──→ FastAPI Backend
  │                                                │
  │                                          ┌─────┴──────┐
  │                                          │            │
  │                                      Gemini +    BigQuery
  │                                    Vertex AI     (logging)
  │                                    Search         │
  │                                          │         │
  └── Web Browser ────────────────────→ React Dashboard
                                        (reads BigQuery,
                                         calls /api/...)
```

---

## The Demo in 3 Minutes

When presenting to judges, show this sequence:

1. **SMS** — text *"What are my voting rights?"* to the shortcode. Show the Gemini-powered reply arriving on a phone.
2. **Fact-check** — text *"FACT: The president serves a 4-year term"*. Show the MISLEADING verdict.
3. **USSD** — open the AT simulator, dial `*384#`, navigate to Ask a Question, type a question, show the answer.
4. **Dashboard** — open the React app, show the interaction charts populating from BigQuery in real time.
5. **Legislative Tracker** — click a bill, show the plain-language Gemini summary.
6. **Petition** — sign one, show the count increment live.

Each of these is one feature, but together they tell one story: *SautiYetu puts civic power in every Kenyan's hands — regardless of whether they have a smartphone.*

---

*SautiYetu — Our Voice | ATX Google Build With AI Grand Finale*
