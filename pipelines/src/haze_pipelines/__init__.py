"""haze-pipelines: batch ingestion and processing for the climate risk platform.

Data policy (project_profile.md section 3):
- Environmental observations ingested here are real and must carry provenance.
- Synthetic or fixture data must be explicitly labeled ``is_fixture`` and registered
  with treatment ``synthetic-fixture``; it is never presented as observation.
"""

__version__ = "0.1.0"

TOOL_NAME = "haze-pipelines"
