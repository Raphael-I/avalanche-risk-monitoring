"""Local execution entry point."""

from __future__ import annotations

import uvicorn


def main() -> None:
    """Run the FastAPI app with sensible local defaults."""

    uvicorn.run(
        "avalanche_risk_monitoring.services.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()

