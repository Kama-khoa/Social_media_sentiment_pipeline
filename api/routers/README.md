# API router groups

- `public/`: endpoints available without authentication, such as login, product browsing, and search.
- `user/`: endpoints that require an authenticated user, such as account details and product detail change requests.
- `admin/`: admin-only CRUD and operational endpoints.

The URL paths remain backward compatible. The folders describe access level and ownership in the Python codebase.
