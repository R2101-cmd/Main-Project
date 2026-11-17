import json
import os
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


def main():
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    sys.path.insert(0, str(root))
    app = AppTest.from_file("app.py", default_timeout=30)
    app.run()
    result = {
        "initial_run_without_exception": not app.exception,
        "initial_exceptions": [str(e) for e in (app.exception or [])],
        "input_modes": [str(x.label) for x in app.radio],
        "research_label_selector_absent": len(app.selectbox) == 0,
    }
    if app.exception:
        print(json.dumps(result, indent=2))
        return 1
    # Exercise rendering for all three intake modes before submitting a
    # deterministic pasted-text case that requires no network access.
    if app.radio:
        app.radio[0].set_value("Public URL").run()
        result["public_url_mode_renders"] = not app.exception and len(app.text_input) >= 1
        app.radio[0].set_value("Poster image").run()
        result["poster_mode_renders"] = not app.exception and len(app.get("file_uploader")) >= 1
        app.radio[0].set_value("Pasted text").run()
    if not app.text_area:
        result["workflow_run_without_exception"] = False
        result["workflow_exceptions"] = ["advertisement input control missing"]
    else:
        app.text_area[0].set_value("Job title: Data Analyst. Employer: Acme Corp. Location: Bengaluru. Responsibilities include SQL analysis and dashboard reporting.")
        # The second textarea is optional user-supplied public links; leave blank.
        submit = next((button for button in app.button if str(button.label) in {"Review this vacancy", "Assess vacancy evidence"}), None)
        if submit is None:
            result["workflow_run_without_exception"] = False
            result["workflow_exceptions"] = ["assessment submit button missing"]
        else:
            submit.click().run()
            result["workflow_run_without_exception"] = not app.exception
            result["workflow_exceptions"] = [str(e) for e in (app.exception or [])]
            result["result_metrics"] = [str(m.label) + ":" + str(m.value) for m in app.metric]
            result["result_has_authorization_metric"] = any(str(m.label) == "Vacancy authorization" for m in app.metric)
            result["result_has_fraud_outcome"] = any(str(m.label) == "Fraud outcome" for m in app.metric)
    print(json.dumps(result, indent=2))
    return 0 if result.get("initial_run_without_exception") and result.get("public_url_mode_renders") and result.get("poster_mode_renders") and result.get("workflow_run_without_exception") and result.get("result_has_authorization_metric") and result.get("result_has_fraud_outcome") and result["research_label_selector_absent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
