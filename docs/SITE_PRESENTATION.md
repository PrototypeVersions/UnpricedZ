# Paper & Ink site presentation

The site presents the existing risk-1.0.0 experiment through Overview, Forecasts,
a prominent $1,000 Experiment, Results, Research, Methods, and About. The
homepage also links directly to the continuing paper portfolio. The research-2.0.0 direction study
continues under its original specification and retains its original fragment URLs.

No model, target, scoring rule, archived result, or frozen record is changed by
this presentation layer. Annualized volatility is a display conversion of
variance, sqrt(252 × variance). Model ranges are disagreement, not confidence
intervals. Drawdowns use the registered entry price and daily closes.

The home page fetches only risk.json, risk_status.json, and presentation.json.
Historical and synthetic reports load when their views need them. A failed
request retains available data with a visible warning; it never silently
reports a successful refresh. Data & status separates pipeline success, browser
retrieval and forecast freshness. About shows a dated copy of Hub receipts,
compares their file hashes with current exports, and retains late/missing states.
A receipt is evidence of arrival, not proof of exact forecast creation time.

`site_tools/build_context.py` creates disposable presentation.json inside the
Pages artifact, reading up to 60 frozen issues and their recorded resolutions.
It verifies file and resolution references and never writes research records.
It also supplies an NYSE calendar, including holidays, early closes, and DST.
Freshness compares the latest completed session with the next entry open.
The calendar has a finite validity range and an expired calendar is unknown,
not healthy. Unexpected exchange closures still require a calendar update.

The site publisher runs after the existing daily workflows complete, including
failed runs, and rebuilds from current main under the existing publication
concurrency group. Research jobs retain their schedules, computations and record
commits; only the site publisher deploys Pages so generated documents and context
are always included. Registered-program and recovery completions also rebuild
the website. Website-only workflow changes do not rerun research.
The presentation bundle must match both the latest forecast ID and risk report
timestamp before the page uses its history or freshness information.

Frontend CI checks actual DOM rendering with LinkeDOM, resource loading, failure
and recovery states, filtering, target switching, asset details, evidence
separation, preserved routes, and session-aware freshness. Python tests check
read-only context generation, file hashes, resolution references, and exchange
holidays. These tests are not browser visual or screen-reader certification.
After deployment, the publisher checks the live HTML, JavaScript, stylesheet,
forecast JSON and display context against the artifact's exact file hashes.

The registered macro attempt remains linked unmodified, with the all-model
decomposition linked beside it. Synthetic results show each fitted learner,
the EWMA baseline, and the generating-process oracle separately.


`site_tools/build_reference.py` creates readable copies of all research documents,
exact settings, published reports, and frozen forecast/resolution files under
`site/reference/`. The source files are not altered; exact-byte downloads and a
hash manifest accompany the HTML. Markdown links point to on-site readers where
available. Original source code and large input archives retain optional GitHub
links. The generated pages can be read without JavaScript.

`reader.json` carries the public settings, a dated Hub receipt summary, and the
specific frozen direction forecasts that produced the latest portfolio plan.
The plan is joined by its actual signal date, rather than using a newer daily
forecast. Its explanation is hidden if the live-report timestamp does not match.
The portfolio page states the fixed thresholds, cash behavior, simulated costs,
settled-only accounting and unequal strategy/SPY cost treatment. The future
risk-aware stock portfolio is labeled proposed, with no fabricated results.

The reader guide defines the project names, models, timing, training and scoring
terms with worked examples. The trading-research proposal records the discussed
sequence without registering or starting a new experiment. All original direction
routes remain available. No other repository is modified.
