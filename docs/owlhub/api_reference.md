# OwlHub API Reference

## Docs Endpoints

- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Authentication

- `POST /api/v1/auth/token`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/api-keys`

## Skills

- `GET /api/v1/skills`
- `GET /api/v1/skills/{publisher}/{name}`
- `GET /api/v1/skills/{publisher}/{name}/versions`
- `GET /api/v1/skills/{publisher}/{name}/statistics`
- `POST /api/v1/skills`
- `PUT /api/v1/skills/{publisher}/{name}/versions/{version}/state`
- `POST /api/v1/skills/{publisher}/{name}/takedown`

## Governance and Review

- `GET /api/v1/reviews/pending`
- `POST /api/v1/reviews/{review_id}/approve`
- `POST /api/v1/reviews/{review_id}/reject`
- `POST /api/v1/reviews/{review_id}/appeal`
- `GET|POST|DELETE /api/v1/admin/blacklist`
- `GET /api/v1/statistics/export`
- `GET /api/v1/audit`

## Operational

- `GET /health`
- `GET /metrics`
