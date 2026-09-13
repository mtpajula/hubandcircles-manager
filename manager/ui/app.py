"""Streamlit entry: `uv run streamlit run manager/ui/app.py`. Shell of ADMIN-UI-SPEC section 1."""

from pathlib import Path

import streamlit as st

from manager import source_repo, state
from manager.settings import data_dir, load_env
from manager.ui import texts

load_env()
st.set_page_config(page_title=texts.APP_TITLE, layout="wide")

# Not "pages/": Streamlit auto-registers that folder. English file names, Finnish titles from texts.
PAGES = Path(__file__).parent / "views"
navigation = st.navigation(
    [
        st.Page(PAGES / "routes.py", title=texts.PAGE_ROUTES, url_path="routes", default=True),
        st.Page(PAGES / "layers.py", title=texts.PAGE_LAYERS, url_path="layers"),
        st.Page(PAGES / "services.py", title=texts.PAGE_SERVICES, url_path="services"),
        st.Page(PAGES / "reports.py", title=texts.PAGE_REPORTS, url_path="reports"),
        st.Page(PAGES / "themes.py", title=texts.PAGE_THEMES, url_path="themes"),
        st.Page(
            PAGES / "build_publish.py", title=texts.PAGE_BUILD_PUBLISH, url_path="build-publish"
        ),
    ]
)

with st.sidebar:
    st.title(texts.APP_TITLE)
    st.caption(texts.APP_SUBTITLE)

navigation.run()

with st.sidebar:
    st.divider()
    st.subheader(texts.SIDEBAR_SOURCE_DATA)
    source = data_dir()
    if source is None:
        st.caption(texts.DATA_DIR_MISSING)
    else:
        st.caption(source.name)
        try:
            status = source_repo.status(source)
            st.caption(texts.SIDEBAR_CHANGES.format(count=status.changed))
            st.caption(texts.SIDEBAR_BRANCH_AHEAD.format(branch=status.branch, ahead=status.ahead))
        except source_repo.SourceRepoError:
            st.caption(texts.SIDEBAR_NOT_A_REPO)
    last = state.last_publish()
    st.caption(
        texts.SIDEBAR_LAST_PUBLISH.format(when=last.astimezone().strftime("%d.%m.%Y %H:%M"))
        if last
        else texts.SIDEBAR_NO_PUBLISH
    )
