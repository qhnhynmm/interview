"""Entry point for LiveKit interview worker (separate process from API)."""

from app.agents.interview.worker import main

if __name__ == "__main__":
    main()