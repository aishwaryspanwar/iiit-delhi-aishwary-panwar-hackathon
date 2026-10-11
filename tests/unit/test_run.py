import os

import run


def make_frontend(tmp_path):
    frontend = tmp_path / "frontend"
    (frontend / "src").mkdir(parents=True)
    (frontend / "src" / "main.tsx").write_text("export {};", encoding="utf-8")
    (frontend / "dist").mkdir()
    return frontend


def test_frontend_is_rebuilt_only_when_missing_or_older_than_its_sources(tmp_path, monkeypatch):
    frontend = make_frontend(tmp_path)
    index = frontend / "dist" / "index.html"
    monkeypatch.setattr(run, "FRONTEND", frontend)
    monkeypatch.setattr(run, "DIST_INDEX", index)
    assert run.frontend_stale()
    index.write_text("<html></html>", encoding="utf-8")
    source = frontend / "src" / "main.tsx"
    os.utime(source, (1_000_000, 1_000_000))
    os.utime(index, (2_000_000, 2_000_000))
    assert not run.frontend_stale()
    os.utime(source, (3_000_000, 3_000_000))
    assert run.frontend_stale()


def test_requirements_are_reinstalled_when_the_file_changes(tmp_path, monkeypatch):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pandas==3.0.6\n", encoding="utf-8")
    stamp = tmp_path / ".requirements.sha256"
    calls = []
    monkeypatch.setattr(run, "REQUIREMENTS", requirements)
    monkeypatch.setattr(run, "STAMP", stamp)
    monkeypatch.setattr(run.subprocess, "run", lambda command, check: calls.append(command))
    run.ensure_requirements(tmp_path / "python")
    run.ensure_requirements(tmp_path / "python")
    assert len(calls) == 1
    requirements.write_text("pandas==3.0.7\n", encoding="utf-8")
    run.ensure_requirements(tmp_path / "python")
    assert len(calls) == 2


def test_busy_port_is_detected():
    import socket

    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        assert run.port_in_use("127.0.0.1", server.getsockname()[1])
