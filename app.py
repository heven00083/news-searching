import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Kunming Trend-Catcher", layout="wide")
    st.title("Kunming Trend-Catcher (昆明外宣热点捕手)")
    st.caption("Step 0: 环境与项目初始化")
    st.info("下一步将加入：分类配置、数据源接入（Google News RSS / GDELT）、AI 简报与导出。")


if __name__ == "__main__":
    main()
