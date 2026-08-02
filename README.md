# Handwritten Bill Extraction & Model Evaluation

A pipeline that extracts structured data (vendor, invoice number, date, amount,
currency, GST details) from photos of handwritten/semi-handwritten Indian bills
using multiple vision-language models, scores their accuracy against manually
verified ground truth, and pushes extracted expenses into Zoho Books.

## Setup

1. Clone this repo, `cd` into it
2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate        # Mac/Linux
   venv\Scripts\Activate.ps1       # Windows PowerShell
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your own API keys:
   ```
   GEMINI_API_KEY=
   OPENROUTER_API_KEY=
   ANTHROPIC_API_KEY=
   OPENAI_API_KEY=
   ZOHO_CLIENT_ID=
   ZOHO_CLIENT_SECRET=
   ZOHO_REFRESH_TOKEN=
   ZOHO_ORG_ID=
   ```

## Run

```
cd extraction && python run_extraction.py
cd ../eval && python scorer.py
cd ../zoho && python create_expense.py    # optional — pushes select bills to Zoho Books
```

The extraction script saves progress incrementally to `results/raw_extractions.json`
after every API call, so it can be safely interrupted and resumed without losing
completed work or re-spending API credits on bills already processed.

## Dataset

12 handwritten/semi-handwritten Indian bills, collected as phone photos, covering
a deliberately wide spread of formats and vendor types:

| Bill | Vendor | Type |
|---|---|---|
| bill_01 | Kar Klinik | Auto parts (vehicle bill) |
| bill_02 | Vinayaka Store | Hardware/general store |
| bill_03 | Surendra Jewellers | Jewellery (tax invoice, CGST/SGST) |
| bill_04 | Alwin Tailors | Tailoring |
| bill_05 | Al-Mariyam Dates & Dry Fruits | Groceries (tax invoice) |
| bill_06 | Perfect Computers | Computer parts (estimate, no total written) |
| bill_07 | Adibanee | Textiles/handloom |
| bill_08 | Tata Starbucks Private Ltd | Café/food (semi-printed) |
| bill_09 | Varnamm | Textiles/tailoring |
| bill_10 | Vishal Punjabi Vaishno Bhojanalya | Restaurant |
| bill_11 | Hotel Sagar View | Hotel/restaurant |
| bill_12 | Balaji Cauvery Silk, Arts & Crafts Emporium | Silk/crafts emporium |

Ground truth (`dataset/ground_truth.csv`) was manually transcribed by reading each
physical bill directly, field by field: vendor, invoice number, date, amount,
currency, and any visible GST breakdown.

Several bills were deliberately kept in the dataset despite genuine ambiguity,
since these are realistic edge cases an extraction pipeline needs to handle
gracefully rather than clean, easy examples:
- **bill_04**: date is physically torn off the bill — left blank in ground
  truth rather than guessed, to test whether models also say "null" instead
  of hallucinating a date
- **bill_06**: no total is written on the bill at all, only itemized lines —
  ground truth reflects what's actually on the page, not a computed sum
- **bill_08**: the invoice date field is printed but left blank by the vendor;
  the item subtotal doesn't cleanly match the rounded final total (likely an
  unitemized discount), so ground truth uses the rounded final total as
  printed
- **bill_10, bill_11**: dates are difficult to read even manually; recorded
  where legible, left blank where genuinely ambiguous
- **bill_12**: the bill's own printed math is internally inconsistent
  (line items + CGST + SGST don't sum to the printed "Net Total") — ground
  truth uses the printed Net Total figure rather than "correcting" it, since
  a model should extract what's written, not recompute totals

A small number of initially collected images (from Kenya, Nigeria, the
Dominican Republic, Turkey, the UK, and an Indonesian-language and a
Spanish-language bill) were identified and excluded during dataset review,
since the task specifically scopes to Indian bills.

## Approach

- **Models evaluated**: Gemini (`gemini-3.6-flash`, via Google AI Studio) and
  a free vision model via OpenRouter
  (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`). Claude and OpenAI
  were originally planned as additional comparison points but were excluded
  from this run due to account billing/credit constraints during
  development; the pipeline (`extraction/run_extraction.py`) already
  supports both and they can be added by uncommenting their entries in the
  `MODELS` dict once credentials are funded.
- **Prompt**: identical extraction prompt sent to every model for every bill,
  requesting a fixed JSON schema (vendor, invoice_number, date, amount,
  currency, gst_details), with explicit instruction to return `null` for
  fields that aren't confidently readable rather than guessing. Keeping the
  prompt identical across models isolates model capability as the variable
  being compared, rather than prompt-engineering differences.
- **Images**: sent as-is (no preprocessing/cropping/rotation correction), to
  reflect a realistic "photo straight from a phone" input rather than an
  idealized scan.

## Eval Methodology

Field-level scoring rather than a single blended accuracy number, since
different fields have very different error tolerances:

- **`amount`**: exact numeric match only (tolerant of floating-point
  rounding noise, e.g. 1300 vs 1300.00). A wrong total is a genuine
  bookkeeping error with no partial credit deserved.
- **`date`, `currency`**: exact string match after normalization
  (lowercased, whitespace-trimmed). These are low-ambiguity fields a model
  should get exactly right when the source is legible.
- **`vendor`, `invoice_number`, `gst_details`**: fuzzy string match
  (Levenshtein-based similarity via `rapidfuzz`), full credit at ≥0.85
  similarity, partial credit below that. Handwriting OCR routinely produces
  near-misses on business names (e.g. "Sharma Genral Store" vs "Sharma
  General Store") that are a spelling artifact, not a real extraction
  failure, so exact match would unfairly penalize otherwise-correct reads.
- **Both null/missing**: scored as correct. A model that correctly
  recognizes illegible/absent text and returns `null` should not be
  penalized the same as a model that hallucinates a plausible-looking but
  wrong value — this is arguably the single most important behavior being
  tested on a handwritten-bill dataset, since confident wrong answers are
  more dangerous in a bookkeeping context than honest gaps.

Cost was calculated using each provider's published token pricing applied to
the actual input/output token counts recorded per call (saved alongside each
extraction in `results/raw_extractions.json`), extrapolated to a
cost-per-100-bills estimate for realistic scaling comparison.

## Results

Accuracy by model and field (from `results/accuracy_by_model_field.csv`):

| Model | vendor | invoice_number | date | amount | currency | gst_details | **Overall** |
|---|---|---|---|---|---|---|---|
| **gemini** | 1.00 | 0.96 | 0.67 | 0.92 | 1.00 | 0.54 | **0.846** |
| **openrouter** | 1.00 | 0.83 | 0.50 | 0.75 | 0.75 | 0.50 | **0.721** |

Gemini outperformed the free OpenRouter model on every field except vendor
(tied at perfect accuracy on both). The largest gaps were on `currency`
(100% vs 75%) and `amount` (92% vs 75%) — the two fields with zero tolerance
for error in a bookkeeping context. Both models struggled most on
`gst_details` (~50-54%) and `date` (~50-67%), reflecting genuine ambiguity
in the source bills themselves (see dataset notes above on bills with
torn/illegible dates and inconsistent GST formatting) rather than a
model-specific weakness.

**Cost per 100 bills** (based on actual token usage recorded per call):

| Model | Avg. input tokens/bill | Avg. output tokens/bill* | Est. cost / 100 bills |
|---|---|---|---|
| gemini | 1,276 | 739 | **$0.75** (at paid-tier rate: $1.50/M in, $7.50/M out — the free tier used for this run is rate-limited to 5 requests/minute and not viable at production scale) |
| openrouter | 909 | 3,903 | **$0.00** (confirmed $0 cost in API response regardless of token volume — permanently free-tier model) |

*Includes "thinking"/reasoning tokens, which both providers bill at the
output-token rate.

Notably, the free OpenRouter model used **~5.3x more output tokens per bill**
than Gemini (avg. 3,903 vs 739) — largely reasoning/thinking tokens — while
still scoring lower on accuracy. This is a real efficiency gap, not just a
price gap: even setting cost aside, Gemini reached a better answer using
fewer tokens and (by extension) less latency per bill.

## Recommendation

**Gemini 3.6 Flash is the better choice for this use case**, even accounting
for its small but non-zero cost. At ~$0.75 per 100 bills, the cost is
negligible in absolute terms, and it delivers meaningfully higher accuracy
(84.6% vs 72.1% overall) — particularly on the two fields where errors are
most costly to a bookkeeping pipeline: `amount` and `currency`. An extraction
pipeline that gets the amount wrong on 1 in 4 bills (as the free model does)
creates real downstream reconciliation work; Gemini's 1-in-12 error rate on
amount is a meaningfully lower error surface even if not perfect.

The free OpenRouter model remains a reasonable fallback or budget option —
particularly for high-volume, low-stakes use cases, or as a first-pass
filter that flags bills for human review rather than auto-posting to
accounting software — but is not recommended as the sole extraction engine
for a production bookkeeping pipeline given the accuracy gap on
error-sensitive fields.

**On handwritten vs. digital-style bills specifically**: neither model
showed a large accuracy split by bill type in this run — both struggled
similarly on the most illegible handwriting (e.g. torn dates, ambiguous
digit formatting) regardless of model. This suggests the harder constraint
here is genuinely image legibility, not model capability — meaning
preprocessing (deskewing, contrast enhancement, upscaling) may yield larger
accuracy gains than switching models, and could be a worthwhile next
investment before reaching for a more expensive model tier.

**Not evaluated here, but worth doing before a final production decision**:
Claude and OpenAI's vision models. Both are well-regarded for OCR/document
tasks and were excluded from this run only due to account billing, not any
technical limitation — re-running this same pipeline with those two would
either confirm Gemini's advantage or reveal a stronger option at a similar
cost tier.

## Zoho Books Integration

`zoho/create_expense.py` reads extracted results from
`results/raw_extractions.json` and creates real expense entries via the Zoho
Books API (OAuth2 refresh-token flow). Verified working end-to-end: 3 test
bills (bill_01, bill_02, bill_03) were successfully pushed and appear
correctly in the Zoho Books Expenses ledger with matching vendor, date, and
amount.

## Limitations

- Dataset size (12 bills) is small; error bars on any accuracy percentage
  should be read as indicative, not statistically robust
- Ground truth was manually transcribed by a single person reading each
  physical bill once — it is possible some ground truth entries contain
  transcription errors, particularly on the hardest-to-read bills flagged
  above
- The 0.85 fuzzy-match threshold for vendor/invoice_number/gst_details is a
  reasonable but ultimately subjective judgment call, not a standard
  benchmark
- Only 2 of the originally planned 3+ models were evaluated due to free-tier
  billing/credit constraints on the other providers during development
- No image preprocessing (deskewing, contrast enhancement, cropping) was
  applied; results reflect raw phone-camera photo quality