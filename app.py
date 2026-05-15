import streamlit as st
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).with_name("trend_catcher.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS category_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(category_id, keyword),
            FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()

    existing = {
        row[0]
        for row in conn.execute("SELECT name FROM categories;").fetchall()
        if row and row[0]
    }
    defaults = ["舆情监测", "媒体传播"]
    for name in defaults:
        if name not in existing:
            conn.execute("INSERT INTO categories (name) VALUES (?);", (name,))
    conn.commit()


def list_categories(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    rows = conn.execute("SELECT id, name FROM categories ORDER BY id ASC;").fetchall()
    return [(int(r[0]), str(r[1])) for r in rows]


def create_category(conn: sqlite3.Connection, name: str) -> int:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("分类名不能为空")
    cur = conn.execute("INSERT INTO categories (name) VALUES (?);", (cleaned,))
    conn.commit()
    return int(cur.lastrowid)


def delete_category(conn: sqlite3.Connection, category_id: int) -> None:
    conn.execute("DELETE FROM categories WHERE id = ?;", (category_id,))
    conn.commit()


def list_keywords(conn: sqlite3.Connection, category_id: int) -> list[tuple[int, str]]:
    rows = conn.execute(
        "SELECT id, keyword FROM category_keywords WHERE category_id = ? ORDER BY id ASC;",
        (category_id,),
    ).fetchall()
    return [(int(r[0]), str(r[1])) for r in rows]


def add_keyword(conn: sqlite3.Connection, category_id: int, keyword: str) -> None:
    cleaned = keyword.strip()
    if not cleaned:
        raise ValueError("关键词不能为空")
    conn.execute(
        "INSERT OR IGNORE INTO category_keywords (category_id, keyword) VALUES (?, ?);",
        (category_id, cleaned),
    )
    conn.commit()


def delete_keyword(conn: sqlite3.Connection, keyword_id: int) -> None:
    conn.execute("DELETE FROM category_keywords WHERE id = ?;", (keyword_id,))
    conn.commit()


def first_category_id(categories: list[tuple[int, str]]) -> int | None:
    return categories[0][0] if categories else None


def main() -> None:
    st.set_page_config(page_title="Kunming Trend-Catcher", layout="wide")
    st.title("Kunming Trend-Catcher (昆明外宣热点捕手)")
    st.caption("Step 1: 分类与关键词配置（SQLite 持久化）")

    conn = get_connection()
    init_db(conn)

    categories = list_categories(conn)
    selected_category_id = st.session_state.get("selected_category_id")
    if selected_category_id is None:
        selected_category_id = first_category_id(categories)
        st.session_state["selected_category_id"] = selected_category_id

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
            except sqlite3.IntegrityError:
                st.error("分类名已存在")
            except ValueError as e:
                st.error(str(e))

    if not categories:
        st.sidebar.info("还没有分类。请先创建一个分类。")
    else:
        for category_id, category_name in categories:
            is_selected = category_id == st.session_state.get("selected_category_id")
            with st.sidebar.expander(
                f"📁 {category_name}",
                expanded=is_selected,
            ):
                top_col1, top_col2 = st.columns([0.62, 0.38])
                with top_col1:
                    if is_selected:
                        st.caption("当前分类")
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
                        except ValueError as e:
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

    left, right = st.columns([0.55, 0.45], gap="large")

    with left:
        st.subheader("当前分类")
        chosen_id = st.session_state.get("selected_category_id")
        if chosen_id is None:
            st.warning("还没有分类。请先在左侧创建一个分类。")
        else:
            category_name = next((n for cid, n in categories if cid == chosen_id), "")
            st.write(category_name)

            st.subheader("关键词列表")
            kws = list_keywords(conn, chosen_id)
            if not kws:
                st.info("该分类暂无关键词。")
            else:
                st.table([{"keyword": kw} for _id, kw in kws])

    with right:
        st.subheader("下一步（Step 2）")
        st.write("接入 Google News RSS 与 GDELT 数据源，并将抓取结果写入 SQLite。")


if __name__ == "__main__":
    main()
