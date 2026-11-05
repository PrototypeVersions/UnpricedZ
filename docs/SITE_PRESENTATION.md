# Paper & Ink site presentation

The site presents the existing risk-1.0.0 experiment through Overview, Forecasts,
Results, Research, and About. A prominent $1,000 experiment tab and homepage
link expose the continuing paper portfolio. The research-2.0.0 direction study
continues under its original specification and retains its original fragment URLs.

No model, target, scoring rule, archived result, or frozen record is changed by
this presentation layer. Annualized volatility is a display conversion of
variance, sqrt(252 × variance). Model ranges are disagreement, not confidence
intervals. Drawdowns use the registered entry price and daily closes.

The home page fetches only risk.json, risk_status.json, and presentation.json.
Historical and synthetic reports load when their views need them. A failed
request retains available data with a visible warning; it never silently
reports a successful refresh. Data & status separates pipeline success, browser
retrieval, forecast freshness, and the link to Hub's independent record. It
does not claim to have verified a Hub receipt.

`site_tools/build_context.py` creates disposable presentation.json inside the
Pages artifact, reading up to 60 frozen issues and their recorded resolutions.
It verifies file and resolution references and never writes research records.
It also supplies an NYSE calendar, including holidays, early closes, and DST.
Freshness compares the latest completed session with the next entry open.
The calendar has a finite validity range and an expired calendar is unknown,
not healthy. Unexpected exchange closures still require a calendar update.

The site publisher runs after the existing daily workflows complete, including
failed runs, and rebuilds from current main under the existing publication
concurrency group. The research workflows themselves are unchanged. During
their preceding deployment, expanded history can be temporarily unavailable;
the page explicitly reports that state and continues to show frozen forecasts.
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
