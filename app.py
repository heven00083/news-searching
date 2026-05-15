import streamlit as st

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).with_name("src")))

from storage.models import (
    get_connection,
    init_db,
    list_categories,
    create_category,
    delete_category,
    list_keywords,
    add_keyword,
    delete_keyword,
    first_category_id,
    save_news_items,
    list_news_items,
    clear_news_items,
)
from ingest.google_news_rss import fetch_by_keyword


def run_fetch(conn, category_id: int, keywords: list[str], progress_callback=None):
    all_items = []
    total = len(keywords)
    for i, kw in enumerate(keywords):
        try:
            items = fetch_by_keyword(kw, category_id)
            all_items.extend([item.to_dict() for item in items])
        except Exception:
            pass
        if progress_callback:
            progress_callback(i + 1, total)
    if all_items:
        saved = save_news_items(conn, all_items)
        return len(all_items), saved
    return 0, 0


st.set_page_config(page_title="Kunming Trend-Catcher", layout="wide")
st.title("Kunming Trend-Catcher (昆明外宣热点捕手)")
st.caption("Step 2: GDELT 全球媒体数据接入 — 抓取 · 入库 · 展示")

if "fetch_done" not in st.session_state:
    st.session_state["fetch_done"] = False

conn = get_connection()
init_db(conn)

categories = list_categories(conn)
if "selected_category_id" not in st.session_state:
    st.session_state["selected_category_id"] = first_category_id(categories)

st.sidebar.header("分类与关键词")

with st.sidebar.expander("➕ 新建分类", expanded=False):
    st.caption("分类名称")
    new_category_name = st.text_input(
        "分类名称",
        placeholder="例如：涉华负面、签证政策、旅游口碑",
        key="new_category_name",
        label_visibility="collapsed",
    )
    if st.button("创建分类", key="create_category_btn"):
        try:
            new_id = create_category(conn, new_category_name)
            st.session_state["selected_category_id"] = new_id
            st.session_state["new_category_name"] = ""
            st.rerun()
        except Exception as e:
            st.error(str(e))

if not categories:
    st.sidebar.info("还没有分类。请先创建一个分类。")
else:
    for category_id, category_name in categories:
        is_selected = category_id == st.session_state.get("selected_category_id")
        with st.sidebar.expander(f"📁 {category_name}", expanded=is_selected):
            top_col1, top_col2 = st.columns([0.62, 0.38])
            with top_col1:
                if is_selected:
                    st.caption("✅ 当前分类")
                else:
                    st.caption(" ")
            with top_col2:
                if st.button("设为当前", key=f"select_cat_{category_id}"):
                    st.session_state["selected_category_id"] = category_id
                    st.rerun()

            st.caption("关键词")
            kw_input_key = f"kw_input_{category_id}"
            kw_cols = st.columns([0.72, 0.28])
            with kw_cols[0]:
                st.text_input(
                    "添加关键词",
                    placeholder="例如：China travel",
                    key=kw_input_key,
                    label_visibility="collapsed",
                )
            with kw_cols[1]:
                if st.button("添加", key=f"add_kw_btn_{category_id}"):
                    try:
                        add_keyword(conn, category_id, st.session_state.get(kw_input_key, ""))
                        st.session_state[kw_input_key] = ""
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

            kws = list_keywords(conn, category_id)
            if not kws:
                st.caption("暂无关键词")
            else:
                for kw_id, kw in kws:
                    row_col1, row_col2 = st.columns([0.78, 0.22])
                    with row_col1:
                        st.write(kw)
                    with row_col2:
                        if st.button("删除", key=f"del_kw_{kw_id}"):
                            delete_keyword(conn, kw_id)
                            st.rerun()

            st.divider()
            danger_key = f"danger_del_cat_{category_id}"
            danger = st.checkbox("我确认要删除该分类", key=danger_key)
            if st.button("删除分类", key=f"del_cat_btn_{category_id}", disabled=not danger):
                delete_category(conn, category_id)
                updated = list_categories(conn)
                st.session_state["selected_category_id"] = first_category_id(updated)
                st.session_state[danger_key] = False
                st.rerun()

chosen_id = st.session_state.get("selected_category_id")

left, right = st.columns([0.6, 0.4], gap="large")

with left:
    st.subheader("热点列表")

    if chosen_id is None:
        st.warning("请先在左侧选择一个分类。")
    else:
        kws = list_keywords(conn, chosen_id)
        kw_list = [kw for _, kw in kws]

        col_refresh, col_clear, col_count = st.columns([1, 1, 2])
        with col_refresh:
            refresh_disabled = len(kw_list) == 0
            if st.button("🔄 抓取热点", use_container_width=True, disabled=refresh_disabled):
                if kw_list:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    status_text.caption("正在抓取 Google News RSS...")

                    def progress_callback(current: int, total: int):
                        progress_bar.progress(current / total)
                        status_text.caption(f"正在抓取关键词 {current}/{total}：{kw_list[current - 1]}")

                    fetched, saved = run_fetch(conn, chosen_id, kw_list, progress_callback)
                    progress_bar.empty()
                    status_text.empty()
                    if saved > 0:
                        st.session_state["fetch_done"] = True
                        st.success(f"抓取完成！共获取 {fetched} 条（新增入库 {saved} 条）")
                    else:
                        st.warning("未抓取到新数据，可能网络连接问题。")

        with col_clear:
            if st.button("🗑 清空记录", use_container_width=True):
                clear_news_items(conn, chosen_id)
                st.session_state["fetch_done"] = False
                st.rerun()

        with col_count:
            total_rows = len(list_news_items(conn, chosen_id, limit=10000))
            st.caption(f"当前分类共 {total_rows} 条记录")

        rows = list_news_items(conn, chosen_id)
        if not rows:
            if kw_list:
                st.info("点击上方「抓取热点」开始采集数据。")
            else:
                st.info("该分类还没有关键词，请先添加关键词再抓取。")
        else:
            st.dataframe(
                [{"标题": r.title, "来源": r.source or "Google News", "时间": r.published or "—", "关键词": r.keyword or "—"} for r in rows],
                use_container_width=True,
                height=420,
                hide_index=True,
            )

            with st.expander("🔗 查看原文链接（可点击）"):
                for r in rows:
                    st.markdown(f"- [{r.title}]({r.url})", unsafe_allow_html=False)

with right:
    st.subheader("使用说明")

    st.markdown("""
    **Step 2 功能说明**

    1. 在左侧选择或新建一个分类
    2. 为该分类添加关键词（如 `Yunnan travel`、`China visa free`）
    3. 点击「抓取热点」，系统将：
       - 通过 Google News RSS 搜索每个关键词
       - 自动去重（同一 URL 不重复入库）
       - 将结果存入本地 SQLite 数据库
    4. 抓取完成后，下方表格展示所有入库记录
    5. 点击链接可直接跳转到原始新闻页面

    **数据源**
    - Google News 搜索 RSS（免费，无需 API Key）
    - 覆盖全球英文媒体新闻源
    """)
    st.divider()
    st.caption("Step 3：接入 GDELT + 打分排序 + DeepSeek AI 简报")
    st.caption("Step 4：添加热度/重要度评级 + Streamlit 定时刷新")
    st.caption("Step 5：Markdown/PDF 导出")


if __name__ == "__main__":
    main() if "main" in dir() else None