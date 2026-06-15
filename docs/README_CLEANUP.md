Cleanup notes:
- Moved backend modules into `backend/` package.
- Moved frontend templates/static into `frontend/` and archived originals under `archive/`.
- Moved utility scripts into `backend/scripts/` and model lists into `models/`.
- Moved flake8 report into `docs/` as `flake8_report.txt`.

Next steps:
- Run local app to verify imports and static serving.
- Remove `archive/` after verification.
