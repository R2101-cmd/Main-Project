from src.ingestion.content_extractor import _main_text, extract_text

def test_extraction_keeps_missing_fields_missing():
    result = extract_text("Title: Data Scientist. Location: Pune. Apply: https://example.com/job")
    assert result.title == "Data Scientist"
    assert result.location == "Pune"
    assert result.salary is None


def test_structured_metadata_extracts_primary_vacancy_and_removes_noise():
    html = '''<html><head>
      <meta property="og:title" content="Data Analyst Intern - Rusaanalytics | LinkedIn">
      <script type="application/ld+json">{"@type":"JobPosting","title":"Data Analyst Intern","hiringOrganization":{"name":"Rusaanalytics"},"jobLocation":{"address":{"addressLocality":"Bengaluru"}},"description":"Analyze data and build reports.","url":"https://rusaanalytics.example/careers/data-analyst-intern"}</script>
    </head><body><nav>Sign in Join now</nav><main><h1>Data Analyst Intern</h1><p>Rusaanalytics is hiring.</p><p>Location: Bengaluru</p></main><aside>Recommended jobs: Other Analyst</aside></body></html>'''
    result = extract_text(html, is_html=True)
    assert result.employer == "Rusaanalytics"
    assert result.title == "Data Analyst Intern"
    assert result.location == "Bengaluru"
    assert "Recommended jobs" not in result.description
    assert result.application_url.endswith("data-analyst-intern")


def test_conflicting_locations_are_not_silently_selected():
    html = '''<script type="application/ld+json">{"@type":"JobPosting","title":"Data Analyst Intern","hiringOrganization":{"name":"Rusaanalytics"},"jobLocation":{"address":{"addressLocality":"Bengaluru"}}}</script><main>Location: Pune</main>'''
    result = extract_text(html, is_html=True)
    assert result.location is None
    assert "location" in result.conflicts
    assert "Conflicting location values" in result.warnings[0]


def test_unknown_fields_remain_null():
    result = extract_text("<main><h1>Data Analyst Intern</h1><p>Work with datasets.</p></main>", is_html=True)
    assert result.title is None
    assert result.employer is None
    assert result.salary is None
    assert result.contact is None


def test_none_empty_and_non_meaningful_html_are_safe():
    assert extract_text(None).description == ""
    assert extract_text("").description == ""
    assert _main_text(None) == ""
    result = extract_text("<html><head><script>var x = 1;</script></head><body><nav>Sign in</nav></body></html>", is_html=True)
    assert result.description == ""
    assert any("meaningful" in warning for warning in result.warnings)


def test_malformed_html_does_not_crash():
    result = extract_text("<main><div class='broken'><p>Title: Analyst", is_html=True)
    assert isinstance(result.description, str)
