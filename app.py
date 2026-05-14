import streamlit as st
import sqlite3
from pathlib import Path
from typing import Iterable


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


def create_category(conn: sqlite3.Connection, name: str) -> None:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("分类名不能为空")
    conn.execute("INSERT INTO categories (name) VALUES (?);", (cleaned,))
    conn.commit()


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


def category_picker(
    *,
    categories: Iterable[tuple[int, str]],
    selected_category_id: int | None,
) -> tuple[int | None, list[str]]:
    ids: list[int] = []
    names: list[str] = []
    for cid, cname in categories:
        ids.append(cid)
        names.append(cname)

    if not ids:
        return None, []

    if selected_category_id in ids:
        index = ids.index(selected_category_id)
    else:
        index = 0

    chosen_name = st.selectbox("当前分类", names, index=index)
    chosen_id = ids[names.index(chosen_name)]
    return chosen_id, names


def main() -> None:
    st.set_page_config(page_title="Kunming Trend-Catcher", layout="wide")
    st.title("Kunming Trend-Catcher (昆明外宣热点捕手)")
    st.caption("Step 1: 分类与关键词配置（SQLite 持久化）")

    conn = get_connection()
    init_db(conn)

    st.sidebar.header("配置")

    categories = list_categories(conn)
    selected_category_id = st.session_state.get("selected_category_id")
    chosen_id, _names = category_picker(
        categories=categories,
        selected_category_id=selected_category_id,
    )
    st.session_state["selected_category_id"] = chosen_id

    with st.sidebar.form("create_category_form"):
        new_name = st.text_input("新建分类", placeholder="例如：涉华负面、签证政策、旅游口碑")
        submitted = st.form_submit_button("创建")
        if submitted:
            try:
                create_category(conn, new_name)
                st.success("已创建分类")
                st.session_state["selected_category_id"] = None
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("分类名已存在")
            except ValueError as e:
                st.error(str(e))

    if chosen_id is not None:
        st.sidebar.divider()
        st.sidebar.subheader("关键词")

        with st.sidebar.form("add_keyword_form"):
            new_kw = st.text_input("添加关键词", placeholder="例如：China travel")
            kw_submitted = st.form_submit_button("添加")
            if kw_submitted:
                try:
                    add_keyword(conn, chosen_id, new_kw)
                    st.success("已添加关键词")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

        kws = list_keywords(conn, chosen_id)
        if not kws:
            st.sidebar.caption("当前分类还没有关键词。")
        else:
            for kw_id, kw in kws:
                col1, col2 = st.sidebar.columns([0.78, 0.22])
                with col1:
                    st.write(kw)
                with col2:
                    if st.button("删除", key=f"del_kw_{kw_id}"):
                        delete_keyword(conn, kw_id)
                        st.rerun()

        st.sidebar.divider()
        danger = st.sidebar.checkbox("我确认要删除该分类")
        if st.sidebar.button("删除当前分类", disabled=not danger):
            delete_category(conn, chosen_id)
            st.session_state["selected_category_id"] = None
            st.rerun()

    left, right = st.columns([0.55, 0.45], gap="large")

    with left:
        st.subheader("当前分类")
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
