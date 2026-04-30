# Data

Store sample, seed, and reference datasets here.

## Rules

- **No secrets or credentials.** Use `.env` or a secrets manager.
- **No large binary files.** Use Git LFS or an external object store and reference by URL.
- Checked-in files should be small samples only (< 1 MB).

## Structure

```
data/
├── README.md
├── sample_input.json    # Example API payload
└── seed.sql             # Database seed script (placeholder)
```
