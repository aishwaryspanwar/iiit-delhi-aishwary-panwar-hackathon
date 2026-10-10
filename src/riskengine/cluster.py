from src.stream.engine import StreamResult, consensus_targets, run_stream

__all__ = ["StreamResult", "build_events", "build_stream", "consensus_targets"]


def build_stream(signals: list[dict]) -> StreamResult:
    return run_stream(signals)


def build_events(signals: list[dict]) -> list[dict]:
    return run_stream(signals).events
