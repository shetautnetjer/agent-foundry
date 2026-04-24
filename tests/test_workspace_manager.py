from foundry.tools.workspace_manager import WorkspaceManager


def test_workspace_manager_copies_project_without_git_or_caches(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    (source / "src").mkdir()
    (source / "src" / "app.py").write_text("print('hello')\n")
    (source / ".git").mkdir()
    (source / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (source / "node_modules").mkdir()
    (source / "node_modules" / "x.js").write_text("ignored\n")

    manager = WorkspaceManager(tmp_path / "workspaces")
    workspace = manager.create_workspace("demo", "task_1", source)

    assert (workspace.repo_path / "src" / "app.py").read_text() == "print('hello')\n"
    assert not (workspace.repo_path / ".git").exists()
    assert not (workspace.repo_path / "node_modules").exists()
    assert (source / "src" / "app.py").exists()


def test_workspace_manager_creates_missing_source_workspace_with_diagnostic(tmp_path):
    manager = WorkspaceManager(tmp_path / "workspaces")
    workspace = manager.create_workspace("missing", "task_1", tmp_path / "nope")

    assert workspace.source_exists is False
    assert workspace.repo_path.exists()
    assert "missing" in workspace.diagnostic.lower()
