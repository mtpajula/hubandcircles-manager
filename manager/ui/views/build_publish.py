"""Build & publish page: the three-step workflow of ADMIN-UI-SPEC section 7.

Thin by rule 8: every button calls manager.* functions and shows their result. Results are
kept in st.session_state so they survive the rerun that every click causes. Readiness of steps
2 and 3 follows one rule, build.is_stale(): dist/catalog.json older than the source data.
"""

import time
from datetime import datetime

import streamlit as st

from manager import source_repo, state
from manager.build import BuildError, build, is_stale
from manager.publish import PublishError, frontend_path, preview, publish, read_settings
from manager.publish.targets import github_pages
from manager.settings import ROOT, data_dir, load_env
from manager.ui import texts
from manager.validate import CHECKS

PREVIEW_PORT = 8765
PREVIEW_URL = f"http://127.0.0.1:{PREVIEW_PORT}"

load_env()
st.title(texts.PAGE_BUILD_PUBLISH)
st.caption(texts.BUILD_PUBLISH_INTRO)

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
frontend_missing = not frontend.is_dir()


def cli(command: str) -> None:
    st.caption(texts.CLI_EQUIVALENT.format(command=command))


def clock(when: datetime) -> str:
    return when.astimezone().strftime("%H:%M:%S")


# --- 1 · Build -------------------------------------------------------------------------------
with st.container(border=True):
    st.subheader(texts.STEP_BUILD_HEADER)
    st.caption(texts.STEP_BUILD_INTRO)
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
                    time=clock(state.mark_built()), seconds=round(time.monotonic() - started, 1)
                )
    cli("python -m manager build")

    report = st.session_state.get("build_report")
    if report is None:
        previous = state.last_build()
        if previous is not None:
            st.caption(
                texts.BUILD_PREVIOUS.format(when=previous.astimezone().strftime("%d.%m.%Y %H:%M"))
            )
    else:
        st.caption(st.session_state["build_finished"])
        routes, first_visit, warnings = st.columns(3)
        routes.metric(texts.METRIC_ROUTES, report.route_count)
        first_visit.metric(texts.METRIC_FIRST_VISIT, f"{report.first_visit_bytes / 1024:.1f} kB")
        warnings.metric(texts.METRIC_WARNINGS, len(report.warnings))
        st.markdown(f"**{texts.CHECKS_HEADER}**")
        for check in CHECKS:
            findings = report.findings_by_check.get(check, [])
            warnings = [f for f in findings if f.level == "warning"]
            name = texts.CHECK_NAMES[check]
            if not findings:
                st.markdown(texts.CHECK_PASSED.format(name=name))
                continue
            if warnings:
                st.markdown(texts.CHECK_WARNING.format(name=name, count=len(warnings)))
            else:
                st.markdown(texts.CHECK_INFO.format(name=name, count=len(findings)))
            with st.expander(texts.CHECK_SHOW):
                for finding in findings:
                    st.text(finding.message)
        st.markdown(f"**{texts.COVERAGE_HEADER}**")
        labels = texts.COVERAGE_COLUMNS
        st.dataframe(
            [
                {
                    labels["theme"]: row["theme"],
                    labels["slot"]: texts.COVERAGE_SLOT_NAMES[row["slot"]],
                    labels["item"]: texts.KEY_FIGURE_NAMES.get(
                        row["item"], texts.BAND_LANE_NAMES.get(row["item"], row["item"])
                    ),
                    labels["routes"]: texts.COVERAGE_ROUTES.format(
                        with_data=row["routes_with_data"], routes=row["routes"]
                    ),
                }
                for row in report.presentation_coverage
            ],
            width="stretch",
            hide_index=True,
        )

stale = is_stale(source, dist)  # after the build button, so a fresh build counts at once

# --- 2 · Esikatselu --------------------------------------------------------------------------
with st.container(border=True):
    st.subheader(texts.STEP_PREVIEW_HEADER)
    st.caption(texts.STEP_PREVIEW_INTRO)
    if frontend_missing:
        st.warning(texts.FRONTEND_MISSING)
    process = st.session_state.get("preview_process")
    if process is not None and process.poll() is not None:
        st.session_state.pop("preview_process")  # exited on its own
        process = None
        st.error(texts.PREVIEW_FAILED)
        st.code(preview.log_tail())
    if process is None:
        if st.button(texts.BUTTON_PREVIEW, key="preview_start", disabled=stale or frontend_missing):
            started = preview.start_background(source, dist, frontend, PREVIEW_PORT)
            if preview.wait_ready(PREVIEW_PORT, started):
                st.session_state["preview_process"] = started
                st.rerun()
            exit_code = started.poll()
            preview.stop(started)
            st.error(f"{texts.PREVIEW_FAILED} (exit {exit_code})")
            st.code(preview.log_tail())
        if stale:
            st.caption(texts.BUILD_FIRST)
    else:
        open_column, stop_column = st.columns(2)
        open_column.link_button(texts.BUTTON_PREVIEW_OPEN, PREVIEW_URL)
        if stop_column.button(texts.BUTTON_PREVIEW_STOP, key="preview_stop"):
            preview.stop(st.session_state.pop("preview_process"))
            st.info(texts.PREVIEW_STOPPED)
    st.caption(texts.PREVIEW_KEEPS_RUNNING)
    cli(f"python -m manager preview --frontend {frontend} --port {PREVIEW_PORT}")

# --- 3 · Julkaise ----------------------------------------------------------------------------
with st.container(border=True):
    st.subheader(texts.STEP_PUBLISH_HEADER)
    st.caption(texts.STEP_PUBLISH_INTRO)

    selected = [
        t
        for t in settings.targets
        if st.checkbox(
            " · ".join(filter(None, [t.id, t.type, t.repo, t.project, t.path])),
            value=True,
            key=f"target_{t.id}",
        )
    ]
    if settings.frontend.path:
        frontend_label = str(frontend)
    else:
        frontend_label = texts.FRONTEND_PINNED.format(
            repo=settings.frontend.repo, version=settings.frontend.version
        )
    st.caption(texts.FRONTEND_CAPTION.format(frontend=frontend_label))

    save_source = False
    message = texts.COMMIT_MESSAGE_DEFAULT
    try:
        repo = source_repo.status(source)
    except source_repo.SourceRepoError:
        st.caption(f"{texts.SIDEBAR_SOURCE_DATA}: {texts.SIDEBAR_NOT_A_REPO}")
    else:
        st.caption(
            texts.SOURCE_REPO_STATUS.format(
                name=source.name, branch=repo.branch, changed=repo.changed, ahead=repo.ahead
            )
        )
        if repo.changed + repo.ahead > 0:
            save_source = st.checkbox(texts.SAVE_SOURCE_DATA, value=True, key="save_source")
            message = st.text_input(
                texts.COMMIT_MESSAGE_LABEL, value=texts.COMMIT_MESSAGE_DEFAULT, key="commit_message"
            ).strip()
        else:
            st.caption(texts.SOURCE_REPO_CLEAN)

    not_ready = stale or frontend_missing or not selected
    if st.button(texts.BUTTON_PUBLISH, type="primary", key="publish", disabled=not_ready):
        published_at = None
        succeeded = False
        with st.status(texts.PUBLISH_RUNNING) as status:
            try:
                bundle = publish(source, dist, frontend, ROOT, [t.id for t in selected])
                st.write(
                    texts.PUBLISH_BUNDLE_LINE.format(
                        files=bundle.file_count, mib=f"{bundle.total_bytes / 2**20:.2f}"
                    )
                )
                for line in bundle.published:
                    st.write(line)
                published_at = state.mark_published()
                if save_source and message:
                    sha = source_repo.commit_and_push(source, message)
                    st.write(
                        texts.PUBLISH_SOURCE_NOTHING
                        if sha == "nothing to commit"
                        else texts.PUBLISH_SOURCE_LINE.format(sha=sha)
                    )
            except (PublishError, source_repo.SourceRepoError) as e:
                status.update(label=texts.PUBLISH_FAILED, state="error")
                st.error(str(e))
            else:
                status.update(label=texts.PUBLISH_DONE, state="complete")
                succeeded = True
        if succeeded and published_at is not None:
            st.success(texts.PUBLISHED_AT.format(time=clock(published_at)))
            for target in selected:
                url = github_pages.site_url(target) if target.type == "github-pages" else None
                if url:
                    st.link_button(texts.BUTTON_OPEN_SITE, url)
                    st.caption(texts.PAGES_UPDATES_SOON)
    if stale:
        st.caption(texts.BUILD_FIRST)
    elif frontend_missing:
        st.caption(texts.FRONTEND_MISSING)
    elif not selected:
        st.caption(texts.NO_TARGETS)
    st.caption(
        texts.CLI_EQUIVALENT_BOTH.format(
            first="python -m manager publish" + "".join(f" --target {t.id}" for t in selected),
            second=f'git -C {source} add -A && git commit -m "{message}" && git push',
        )
    )
