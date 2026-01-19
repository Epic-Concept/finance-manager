# API Overview

## Introduction

The Finance Manager API provides RESTful endpoints for managing personal finances.

## Base URL

```
Development: http://localhost:8000
Production:  TBD
```

## Response Format

All responses are JSON formatted.

### Success Response

```json
{
  "data": { ... },
  "message": "Optional success message"
}
```

### Error Response

```json
{
  "detail": "Error description"
}
```

## HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

## Endpoints

### Health Check

```http
GET /health
```

Returns the API health status and version.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

### Root

```http
GET /
```

Returns basic API information.

**Response:**
```json
{
  "message": "Finance Manager API",
  "version": "0.1.0"
}
```

## Rate Limiting

TBD - Rate limiting implementation pending.

## Authentication

TBD - Authentication implementation pending.
