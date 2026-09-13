"""Build & publish page (ADMIN-UI-SPEC section 7), limited to what the package implements now.

Thin by rule 8: every button calls one manager.* function and shows its result. Results are
kept in st.session_state so they survive the rerun that every click causes.
"""

import time
from datetime import UTC, datetime

import streamlit as st

from manager import source_repo, state
from manager.build import BuildError, build
from manager.publish import PublishError, frontend_path, preview, publish, read_settings
from manager.settings import ROOT, data_dir, load_env
from manager.ui import texts
from manager.validate import CHECKS

PREVIEW_PORT = 8765
PREVIEW_URL = f"http://127.0.0.1:{PREVIEW_PORT}"

load_env()
st.title(texts.PAGE_BUILD_PUBLISH)

source = data_dir()
if source is None:
    st.error(texts.DATA_DIR_MISSING)
    st.stop()
dist = ROOT / "dist"
try:
    settings = read_settings(source)
except PublishError as e:
    st.error(str(e))
    st.stop()
frontend = frontend_path(source, settings)


def cli(command: str) -> None:
    st.caption(texts.CLI_EQUIVALENT.format(command=command))


# --- Build -----------------------------------------------------------------------------------
st.header(texts.BUILD_HEADER)
build_column, preview_column = st.columns(2)

with build_column:
    if st.button(texts.BUTTON_BUILD, type="primary", key="build"):
        with st.status(texts.BUILD_RUNNING) as status:
            started = time.monotonic()
            try:
                report = build(source, dist)
            except BuildError as e:
                status.update(label=texts.BUILD_FAILED, state="error")
                st.session_state.pop("build_report", None)
                st.error(str(e))
            else:
                status.update(label=texts.BUILD_DONE, state="complete")
                st.session_state["build_report"] = report
                st.session_state["build_finished"] = texts.BUILD_FINISHED_AT.format(
                    time=datetime.now(UTC).astimezone().strftime("%H:%M:%S"),
                    seconds=round(time.monotonic() - started, 1),
                )
    cli("python -m manager build")

with preview_column:
    if not frontend.is_dir():
        st.warning(texts.FRONTEND_MISSING.format(path=frontend))
    process = st.session_state.get("preview_process")
    if process is not None and process.poll() is not None:
        st.session_state.pop("preview_process")  # exited on its own
        process = None
        st.error(texts.PREVIEW_FAILED)
        st.code(preview.log_tail())
    if process is None:
        if st.button(texts.BUTTON_PREVIEW, key="preview_start", disabled=not frontend.is_dir()):
            started = preview.start_background(source, dist, frontend, PREVIEW_PORT)
            if preview.wait_ready(PREVIEW_PORT, started):
                st.session_state["preview_process"] = started
                st.rerun()
            preview.stop(started)
            st.error(texts.PREVIEW_FAILED)
            st.code(preview.log_tail())
    else:
        st.success(texts.PREVIEW_RUNNING.format(url=PREVIEW_URL))
        if st.button(texts.BUTTON_PREVIEW_STOP, key="preview_stop"):
            preview.stop(st.session_state.pop("preview_process"))
            st.info(texts.PREVIEW_STOPPED)
    cli(f"python -m manager preview --frontend {frontend} --port {PREVIEW_PORT}")

report = st.session_state.get("build_report")
if report is not None:
    st.caption(st.session_state["build_finished"])
    routes, first_visit, warnings = st.columns(3)
    routes.metric(texts.METRIC_ROUTES, report.route_count)
    first_visit.metric(texts.METRIC_FIRST_VISIT, f"{report.first_visit_bytes / 1024:.1f} kB")
    warnings.metric(texts.METRIC_WARNINGS, len(report.warnings))

    st.subheader(texts.CHECKS_HEADER)
    for check in CHECKS:
        messages = report.warnings_by_check.get(check, [])
        name = texts.CHECK_NAMES[check]
        if not messages:
            st.markdown(texts.CHECK_PASSED.format(name=name))
        else:
            st.markdown(texts.CHECK_WARNING.format(name=name, count=len(messages)))
            with st.expander(texts.CHECK_SHOW):
                for message in messages:
                    st.text(message)

# --- Publish ---------------------------------------------------------------------------------
st.header(texts.PUBLISH_HEADER)
if settings.frontend.path:
    frontend_label = str(frontend)
else:
    frontend_label = texts.FRONTEND_PINNED.format(
        repo=settings.frontend.repo, version=settings.frontend.version
    )
st.caption(texts.FRONTEND_CAPTION.format(frontend=frontend_label))

if not settings.targets:
    st.info(texts.NO_TARGETS)
selected = [
    t.id
    for t in settings.targets
    if st.checkbox(
        " · ".join(filter(None, [t.id, t.type, t.repo, t.project, t.path])),
        value=True,
        key=f"target_{t.id}",
    )
]
if st.button(texts.BUTTON_PUBLISH, type="primary", key="publish", disabled=not settings.targets):
    if not selected:
        st.warning(texts.PUBLISH_NO_SELECTION)
    else:
        with st.status(texts.PUBLISH_RUNNING) as status:
            try:
                bundle = publish(source, dist, frontend, ROOT, selected)
            except PublishError as e:
                status.update(label=texts.PUBLISH_FAILED, state="error")
                st.error(str(e))
            else:
                status.update(label=texts.PUBLISH_DONE, state="complete")
                st.text(bundle.text())
                if bundle.published:
                    state.mark_published()
                    st.text("\n".join([texts.PUBLISHED_TO, *(f"  {x}" for x in bundle.published)]))
cli("python -m manager publish" + "".join(f" --target {t}" for t in selected))

# --- Source data -----------------------------------------------------------------------------
st.header(texts.SOURCE_REPO_HEADER)
try:
    repo = source_repo.status(source)
except source_repo.SourceRepoError as e:
    st.warning(f"{texts.SIDEBAR_NOT_A_REPO}: {e}")
else:
    st.caption(
        texts.SOURCE_REPO_STATUS.format(
            name=source.name, branch=repo.branch, changed=repo.changed, ahead=repo.ahead
        )
    )
    message = st.text_input(
        texts.COMMIT_MESSAGE_LABEL, value=texts.COMMIT_MESSAGE_DEFAULT, key="commit_message"
    )
    if st.button(texts.BUTTON_COMMIT_PUSH, key="commit_push", disabled=not message.strip()):
        with st.status(texts.COMMIT_RUNNING) as status:
            try:
                result = source_repo.commit_and_push(source, message.strip())
            except source_repo.SourceRepoError as e:
                status.update(label=texts.COMMIT_FAILED, state="error")
                st.error(str(e))
            else:
                status.update(label=texts.COMMIT_DONE, state="complete")
                st.text(texts.COMMIT_NOTHING if result == "nothing to commit" else result)
    cli(f'git -C {source} add -A && git commit -m "{message}" && git push')
