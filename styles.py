import streamlit as st


def load_css():
    st.markdown(
        """
        <style>

        /* ============================================================
           ОБЩАЯ ШИРИНА КОНТЕНТА
           ============================================================ */

        .main > div {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }

        .block-container {
            padding-top: 3rem !important;
        }

        section.main > div {
            max-width: 100% !important;
        }

        .stPlotlyChart {
            width: 100% !important;
        }

        .stDataFrame {
            width: 100% !important;
        }

        .stDataFrame > div {
            width: 100% !important;
        }


        /* ============================================================
           ОБЩИЕ КНОПКИ
           ============================================================ */

        div.stButton > button {
            width: 100%;
        }


        /* ============================================================
           ПЛИТКИ ТОП-ОТЧЕТОВ
           ============================================================ */

        .st-key-tile_0 button,
        .st-key-tile_1 button,
        .st-key-tile_2 button,
        .st-key-tile_3 button,
        .st-key-tile_4 button {

            width: 100% !important;

            min-height: 130px !important;
            height: auto !important;

            white-space: normal !important;
            text-align: center !important;

            line-height: 1.5 !important;

            padding: 20px 12px !important;

            border-radius: 16px !important;

            font-weight: 500 !important;
            font-size: 14px !important;

            transition:
                all 0.3s cubic-bezier(0.4, 0, 0.2, 1)
                !important;

            display: flex !important;
            flex-direction: column !important;

            justify-content: center !important;
            align-items: center !important;

            cursor: pointer !important;
        }


        /* ============================================================
           ПЛИТКИ — СВЕТЛАЯ ТЕМА
           ============================================================ */

        [data-theme="light"] .st-key-tile_0 button,
        [data-theme="light"] .st-key-tile_1 button,
        [data-theme="light"] .st-key-tile_2 button,
        [data-theme="light"] .st-key-tile_3 button,
        [data-theme="light"] .st-key-tile_4 button {

            background: linear-gradient(
                145deg,
                #ffffff,
                #f8fafc
            ) !important;

            border: 1px solid #e8ecf0 !important;

            color: #1a1a2e !important;

            box-shadow:
                0 2px 8px rgba(0, 0, 0, 0.06)
                !important;
        }


        [data-theme="light"] .st-key-tile_0 button:hover,
        [data-theme="light"] .st-key-tile_1 button:hover,
        [data-theme="light"] .st-key-tile_2 button:hover,
        [data-theme="light"] .st-key-tile_3 button:hover,
        [data-theme="light"] .st-key-tile_4 button:hover {

            transform: translateY(-6px) !important;

            box-shadow:
                0 12px 28px rgba(33, 150, 243, 0.2)
                !important;

            border-color: #2196F3 !important;

            background: linear-gradient(
                145deg,
                #ffffff,
                #e3f2fd
            ) !important;
        }


        /* ============================================================
           ПЛИТКИ — ТЕМНАЯ ТЕМА
           ============================================================ */

        [data-theme="dark"] .st-key-tile_0 button,
        [data-theme="dark"] .st-key-tile_1 button,
        [data-theme="dark"] .st-key-tile_2 button,
        [data-theme="dark"] .st-key-tile_3 button,
        [data-theme="dark"] .st-key-tile_4 button {

            background: linear-gradient(
                145deg,
                #262730,
                #1f2027
            ) !important;

            border: 1px solid #3a3b45 !important;

            color: #ffffff !important;

            box-shadow:
                0 2px 8px rgba(0, 0, 0, 0.25)
                !important;
        }


        [data-theme="dark"] .st-key-tile_0 button:hover,
        [data-theme="dark"] .st-key-tile_1 button:hover,
        [data-theme="dark"] .st-key-tile_2 button:hover,
        [data-theme="dark"] .st-key-tile_3 button:hover,
        [data-theme="dark"] .st-key-tile_4 button:hover {

            transform: translateY(-6px) !important;

            box-shadow:
                0 12px 28px rgba(33, 150, 243, 0.25)
                !important;

            border-color: #2196F3 !important;

            background: linear-gradient(
                145deg,
                #30313d,
                #252631
            ) !important;
        }


        .st-key-tile_0 button:active,
        .st-key-tile_1 button:active,
        .st-key-tile_2 button:active,
        .st-key-tile_3 button:active,
        .st-key-tile_4 button:active {

            transform: translateY(-2px) !important;
        }


        /* ============================================================
           ТАЙМЕРЫ
           ============================================================ */

        .refresh-timer {
            font-size: 14px;
            font-weight: 400;
            margin-top: 5px;
            margin-bottom: 10px;
        }

        .refresh-countdown {
            font-size: 14px;
            font-weight: 400;
        }


        /* ============================================================
           КАРУСЕЛЬ ОТЧЕТОВ
           ============================================================ */

        .carousel-counter {
            text-align: center;

            font-size: 18px;
            font-weight: 600;

            margin-top: 15px;
            margin-bottom: 15px;

            padding: 18px;

            background: var(--secondary-background-color);
            color: var(--text-color) !important;

            border-radius: 10px;
        }

        .carousel-timer {
            text-align: center;

            font-size: 14px;

            margin-bottom: 15px;

            padding: 18px;

            background: var(--secondary-background-color);
            color: var(--text-color);

            border-radius: 10px;
        }


        /* ============================================================
           СТРАНИЦА «РАЗРАБОТКА»
           ============================================================ */

        .suggestion-text {
            white-space: pre-wrap;
            line-height: 1.6;
            font-size: 15px;
            color: inherit !important;
        }

        .suggestion-meta {
            color: rgba(128, 128, 128, 0.9);
            font-size: 13px;
        }

        div[data-testid="stExpander"] {
            border-radius: 12px;
        }

        .suggestion-button-container {
            width: 100%;
        }

        </style>
        """,
        unsafe_allow_html=True
    )