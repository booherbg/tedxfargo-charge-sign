# Examples

Each file is a complete, reproducible build:

```bash
uv run signforge build --params examples/neon-classic.json -o out/open-neon
uv run signforge build --params examples/channel-bold.json -o out/cafe
uv run signforge build --params examples/mini-desk.json -o out/mini
```

Or with artwork instead of text:

```bash
uv run signforge build --art your-logo.svg --style neon --cap-height 250 -o out/logo
```

Before printing a press-fit lens for the first time on YOUR printer/filament,
print the fit ladder and pick the value that snaps:

```bash
uv run signforge coupon -o out/coupons
```
