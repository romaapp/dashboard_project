import os
import html
import streamlit as st

from suggestions import (
    add_suggestion,
    get_suggestions,
    get_suggestion_files,
    get_suggestions_stats
)


# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================

st.set_page_config(
    page_title="Разработка",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

        /* ----------------------------------------------------
           Текст предложения
        ---------------------------------------------------- */

        .suggestion-text {
            white-space: pre-wrap;
            line-height: 1.6;
            font-size: 15px;
            color: inherit !important;
        }


        /* ----------------------------------------------------
           Метаданные
        ---------------------------------------------------- */

        .suggestion-meta {
            color: rgba(128, 128, 128, 0.9);
            font-size: 13px;
        }


        /* ----------------------------------------------------
           Expander
        ---------------------------------------------------- */

        div[data-testid="stExpander"] {
            border-radius: 12px;
        }


        /* ----------------------------------------------------
           Кнопка предложения
        ---------------------------------------------------- */

        .suggestion-button-container {
            width: 100%;
        }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# ДИАЛОГ ДОБАВЛЕНИЯ
# ============================================================

@st.dialog("💡 Новое предложение")
def add_suggestion_dialog():

    st.write(
        "Опишите идею, ошибку или изменение, "
        "которое вы хотели бы добавить."
    )

    title = st.text_input(
        "Тема или краткое описание",
        placeholder="Например: Добавить отчет по заявкам"
    )

    author = st.text_input(
        "Ваше имя",
        placeholder="Введите имя..."
    )

    suggestion = st.text_area(
        "Предложение",
        placeholder=(
            "Подробно опишите, что необходимо "
            "добавить или изменить..."
        ),
        height=180
    )

    uploaded_files = st.file_uploader(
        "📎 Прикрепить файлы",
        type=[
            "png",
            "jpg",
            "jpeg",
            "webp",
            "gif",
            "pdf",
            "xlsx",
            "xls",
            "docx",
            "txt",
            "csv"
        ],
        accept_multiple_files=True,
        help="Можно прикрепить несколько файлов."
    )

    if uploaded_files:

        st.caption(
            f"📎 Прикреплено файлов: {len(uploaded_files)}"
        )

        for file in uploaded_files:

            st.caption(
                f"• {file.name}"
            )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "Отмена",
            use_container_width=True
        ):

            st.rerun()

    with col2:

        if st.button(
            "➕ Добавить предложение",
            type="primary",
            use_container_width=True
        ):

            if not title.strip():

                st.error(
                    "Введите тему или краткое описание."
                )

                return

            if not author.strip():

                st.error(
                    "Введите ваше имя."
                )

                return

            if not suggestion.strip():

                st.error(
                    "Введите текст предложения."
                )

                return

            try:

                add_suggestion(
                    title=title,
                    author=author,
                    suggestion=suggestion,
                    uploaded_files=uploaded_files
                )

                st.success(
                    "✅ Предложение добавлено!"
                )

                st.rerun()

            except Exception as e:

                st.error(
                    f"Не удалось добавить предложение: {e}"
                )


# ============================================================
# ЗАГОЛОВОК
# ============================================================

st.title(
    "🛠️ Разработка"
)

st.caption(
    "Предложения, идеи и задачи по развитию аналитического дашборда."
)


# ============================================================
# КНОПКА + СТАТИСТИКА
# ============================================================

stats = get_suggestions_stats()

col_button, col_total, col_active, col_completed = st.columns(
    [3.2, 2.25, 2.25, 2.25]
)


with col_button:

    if st.button(
        "➕ Предложить изменение",
        type="primary",
        use_container_width=True
    ):

        add_suggestion_dialog()


with col_total:

    st.metric(
        "💡 Всего предложений",
        stats["total"]
    )


with col_active:

    st.metric(
        "🟡 В работе",
        stats["active"]
    )


with col_completed:

    st.metric(
        "🟢 Выполнено",
        stats["completed"]
    )


st.divider()


# ============================================================
# ФИЛЬТР
# ============================================================

filter_value = st.radio(
    "Показывать:",
    [
        "Все",
        "В работе",
        "Выполнено"
    ],
    horizontal=True
)


status_map = {
    "Все": "all",
    "В работе": "active",
    "Выполнено": "completed"
}


suggestions = get_suggestions(
    status_map[filter_value]
)


# ============================================================
# ОТОБРАЖЕНИЕ
# ============================================================

if not suggestions:

    st.info(
        "Предложений пока нет."
    )

else:

    for (
        suggestion_id,
        title,
        author,
        suggestion,
        created_at,
        completed,
        completed_at,
        completed_by
    ) in suggestions:

        # ----------------------------------------------------
        # Совместимость со старыми предложениями
        # ----------------------------------------------------

        if not title:

            title = suggestion.split(
                "\n"
            )[0][:80]


        # ----------------------------------------------------
        # Статус
        # ----------------------------------------------------

        status_text = (
            "🟢 Выполнено"
            if completed
            else "🟡 В работе"
        )


        # ----------------------------------------------------
        # ЗАЯВКА
        #
        # В свернутом виде:
        # тема + автор + статус
        #
        # В раскрытом:
        # текст + дата + вложения
        # ----------------------------------------------------

        with st.expander(
            f"💡 {title}  •  👤 {author}  •  {status_text}",
            expanded=False
        ):

            st.markdown(
                f"""
                <div class="suggestion-meta">
                    📅 {html.escape(str(created_at))}
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                "### Описание"
            )


            # ------------------------------------------------
            # ТЕКСТ
            #
            # Используем st.text, чтобы текст корректно
            # отображался и в светлой, и в темной теме.
            # ------------------------------------------------

            st.text(
                suggestion
            )


            # ------------------------------------------------
            # ВЛОЖЕНИЯ
            # ------------------------------------------------

            files = get_suggestion_files(
                suggestion_id
            )

            if files:

                st.markdown(
                    "### 📎 Вложения"
                )

                for file_data in files:

                    (
                        file_id,
                        original_name,
                        stored_name,
                        file_path,
                        uploaded_at
                    ) = file_data


                    if not os.path.exists(
                        file_path
                    ):

                        continue


                    extension = (
                        os.path.splitext(
                            original_name
                        )[1]
                        .lower()
                    )


                    # ----------------------------------------
                    # ИЗОБРАЖЕНИЕ
                    # ----------------------------------------

                    if extension in [
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".webp",
                        ".gif"
                    ]:

                        with st.expander(
                            f"🖼 {original_name}",
                            expanded=False
                        ):

                            st.image(
                                file_path,
                                use_container_width=True
                            )


                    # ----------------------------------------
                    # ОСТАЛЬНЫЕ ФАЙЛЫ
                    # ----------------------------------------

                    else:

                        with open(
                            file_path,
                            "rb"
                        ) as file:

                            file_bytes = file.read()


                        st.download_button(
                            f"📎 {original_name}",
                            data=file_bytes,
                            file_name=original_name,
                            key=(
                                f"download_file_"
                                f"{file_id}"
                            ),
                            use_container_width=False
                        )


            # ------------------------------------------------
            # ИНФОРМАЦИЯ О ВЫПОЛНЕНИИ
            # ------------------------------------------------

            if completed:

                text = (
                    f"🟢 Выполнено "
                    f"{completed_at or ''}"
                )

                if completed_by:

                    text += (
                        f" • {completed_by}"
                    )

                st.caption(
                    text
                )

