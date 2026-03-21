import hashlib
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

st.set_page_config(page_title="نظام متابعة الاختبارات القصيرة", layout="wide")

DB_PATH = Path("data/app.db")
FILES_ROOT = Path("data/uploads")
OMAN_TZ = ZoneInfo("Asia/Muscat")


def now_oman() -> datetime:
    return datetime.now(OMAN_TZ)


def hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_storage() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    FILES_ROOT.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    init_storage()
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL CHECK(role IN ('admin', 'teacher')),
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                school_id INTEGER,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES schools(id)
            );

            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                school_id INTEGER NOT NULL,
                grade_label TEXT NOT NULL,
                execution_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('submitted', 'in_review', 'approved', 'needs_revision')),
                is_late INTEGER NOT NULL DEFAULT 0,
                latest_version_no INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (teacher_id) REFERENCES users(id),
                FOREIGN KEY (school_id) REFERENCES schools(id)
            );

            CREATE TABLE IF NOT EXISTS quiz_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL,
                version_no INTEGER NOT NULL,
                note_from_teacher TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (quiz_id) REFERENCES quizzes(id),
                UNIQUE (quiz_id, version_no)
            );

            CREATE TABLE IF NOT EXISTS quiz_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_version_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                mime_type TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (quiz_version_id) REFERENCES quiz_versions(id)
            );

            CREATE TABLE IF NOT EXISTS quiz_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL,
                quiz_version_id INTEGER NOT NULL,
                reviewed_by_admin_id INTEGER NOT NULL,
                decision TEXT NOT NULL CHECK(decision IN ('approved', 'needs_revision')),
                official_note TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (quiz_id) REFERENCES quizzes(id),
                FOREIGN KEY (quiz_version_id) REFERENCES quiz_versions(id),
                FOREIGN KEY (reviewed_by_admin_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                quiz_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (teacher_id) REFERENCES users(id),
                FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
            );
            """
        )

        admin_exists = conn.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1").fetchone()
        if not admin_exists:
            conn.execute(
                """
                INSERT INTO users(role, full_name, email, password_hash, created_at)
                VALUES ('admin', 'المشرف الرئيسي', 'admin@example.com', ?, ?)
                """,
                (hash_password("Admin@123"), now_oman().isoformat()),
            )


init_db()


st.markdown(
    """
    <style>
    .stApp, [data-testid="stSidebar"] { direction: rtl; text-align: right; }
    .pill { padding: 6px 10px; border-radius: 999px; font-weight: 600; display: inline-block; }
    .submitted { background: #dbeafe; color: #1e3a8a; }
    .in_review { background: #e0f2fe; color: #075985; }
    .approved { background: #dcfce7; color: #14532d; }
    .needs_revision { background: #fee2e2; color: #7f1d1d; }
    .late { background: #fff7ed; color: #9a3412; }
    </style>
    """,
    unsafe_allow_html=True,
)


def status_label(status: str) -> str:
    return {
        "submitted": "مرفوع",
        "in_review": "تحت المراجعة",
        "approved": "معتمد",
        "needs_revision": "يحتاج تعديل",
    }.get(status, status)


def add_notification(teacher_id: int, quiz_id: int, title: str, message: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO notifications(teacher_id, quiz_id, title, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (teacher_id, quiz_id, title, message, now_oman().isoformat()),
        )


def submission_window(execution_date_str: str):
    exec_date = datetime.fromisoformat(execution_date_str).date()
    start = exec_date - timedelta(days=3)
    end = exec_date - timedelta(days=1)
    today = now_oman().date()
    in_window = start <= today <= end
    is_late = today > end
    return in_window, is_late, start, end, today


def save_files(quiz_version_id: int, files):
    version_dir = FILES_ROOT / f"version_{quiz_version_id}"
    version_dir.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        for f in files:
            safe_name = f.name.replace("/", "_")
            file_path = version_dir / safe_name
            file_path.write_bytes(f.getvalue())
            conn.execute(
                """
                INSERT INTO quiz_files(quiz_version_id, original_filename, storage_path, mime_type, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (quiz_version_id, f.name, str(file_path), getattr(f, "type", None), now_oman().isoformat()),
            )


def login_view():
    st.title("نظام متابعة الاختبارات القصيرة")
    st.info("بيانات تجريبية للمشرف: admin@example.com / Admin@123")

    role = st.radio("نوع الدخول", options=["teacher", "admin"], format_func=lambda r: "معلم" if r == "teacher" else "مشرف")
    email = st.text_input("البريد الإلكتروني")
    password = st.text_input("كلمة المرور", type="password")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("تسجيل الدخول", use_container_width=True):
            with get_conn() as conn:
                user = conn.execute(
                    """
                    SELECT * FROM users
                    WHERE email=? AND role=? AND is_active=1
                    """,
                    (email.strip().lower(), role),
                ).fetchone()

            if not user or user["password_hash"] != hash_password(password):
                st.error("بيانات الدخول غير صحيحة.")
                return

            st.session_state.user = dict(user)
            st.rerun()

    with col2:
        if st.button("نسيت كلمة المرور؟", use_container_width=True):
            if email:
                st.success("تم إرسال رابط استعادة كلمة المرور إلى البريد (نموذج تجريبي).")
            else:
                st.warning("أدخل البريد الإلكتروني أولاً.")



def teacher_dashboard(user):
    st.title(f"مرحبًا {user['full_name']}")
    st.caption("لوحة المعلم")

    t1, t2, t3 = st.tabs(["رفع اختبار", "سجل اختباراتي", "الإشعارات"])

    with t1:
        with st.form("upload_quiz_form", clear_on_submit=True):
            grade = st.selectbox("الصف", ["الخامس", "السادس", "السابع", "الثامن", "التاسع", "العاشر", "الحادي عشر", "الثاني عشر"])
            execution_date = st.date_input("تاريخ التنفيذ")
            files = st.file_uploader(
                "ارفع ملفات الاختبار (PDF/Word/Images)",
                type=["pdf", "doc", "docx", "png", "jpg", "jpeg"],
                accept_multiple_files=True,
            )
            submit = st.form_submit_button("إرسال للمراجعة")

        if submit:
            if not files:
                st.error("يرجى رفع ملف واحد على الأقل.")
            else:
                _, is_late, start, end, today = submission_window(execution_date.isoformat())
                now = now_oman().isoformat()
                with get_conn() as conn:
                    conn.execute(
                        """
                        INSERT INTO quizzes(teacher_id, school_id, grade_label, execution_date, status, is_late, latest_version_no, created_at, updated_at)
                        VALUES (?, ?, ?, ?, 'submitted', ?, 1, ?, ?)
                        """,
                        (user["id"], user["school_id"], grade, execution_date.isoformat(), int(is_late), now, now),
                    )
                    quiz_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                    conn.execute(
                        """
                        INSERT INTO quiz_versions(quiz_id, version_no, created_at)
                        VALUES (?, 1, ?)
                        """,
                        (quiz_id, now),
                    )
                    version_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

                save_files(version_id, files)

                if is_late:
                    st.warning(f"تم الرفع متأخرًا. نافذة الرفع: من {start} إلى {end} (توقيت عُمان). اليوم: {today}")
                else:
                    st.success("تم إرسال الاختبار بنجاح.")

    with t2:
        with get_conn() as conn:
            quizzes = conn.execute(
                """
                SELECT q.*,
                       (SELECT COUNT(*) FROM quiz_versions v WHERE v.quiz_id=q.id) AS versions_count
                FROM quizzes q
                WHERE q.teacher_id=?
                ORDER BY q.created_at DESC
                """,
                (user["id"],),
            ).fetchall()

        if not quizzes:
            st.info("لا توجد اختبارات مرفوعة بعد.")
        else:
            for q in quizzes:
                c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1, 1])
                c1.write(f"**الصف:** {q['grade_label']}")
                c2.write(f"**تاريخ التنفيذ:** {q['execution_date']}")
                c3.markdown(f"<span class='pill {q['status']}'>{status_label(q['status'])}</span>", unsafe_allow_html=True)
                c4.write(f"النسخ: {q['versions_count']}")
                if q["is_late"]:
                    c5.markdown("<span class='pill late'>متأخر</span>", unsafe_allow_html=True)

                with st.expander(f"تفاصيل الاختبار #{q['id']}"):
                    with get_conn() as conn:
                        reviews = conn.execute(
                            """
                            SELECT r.*, a.full_name AS admin_name
                            FROM quiz_reviews r
                            JOIN users a ON a.id=r.reviewed_by_admin_id
                            WHERE r.quiz_id=?
                            ORDER BY r.created_at DESC
                            """,
                            (q["id"],),
                        ).fetchall()
                        versions = conn.execute(
                            """
                            SELECT * FROM quiz_versions WHERE quiz_id=? ORDER BY version_no DESC
                            """,
                            (q["id"],),
                        ).fetchall()

                    st.write("**الملاحظات الرسمية:**")
                    if reviews:
                        for r in reviews:
                            st.write(f"- [{r['created_at'][:16]}] {r['admin_name']}: {r['official_note']}")
                    else:
                        st.caption("لا توجد مراجعات بعد.")

                    st.write("**النسخ السابقة:**")
                    for v in versions:
                        st.write(f"- Version {v['version_no']} — {v['created_at'][:16]}")

                    if q["status"] == "needs_revision":
                        files2 = st.file_uploader(
                            f"رفع نسخة معدلة للاختبار #{q['id']}",
                            type=["pdf", "doc", "docx", "png", "jpg", "jpeg"],
                            accept_multiple_files=True,
                            key=f"reupload_{q['id']}",
                        )
                        note = st.text_area("ملاحظة المعلم (اختياري)", key=f"note_{q['id']}")
                        if st.button("إعادة الرفع", key=f"btn_{q['id']}"):
                            if not files2:
                                st.error("ارفع ملفًا واحدًا على الأقل.")
                            else:
                                with get_conn() as conn:
                                    next_version = q["latest_version_no"] + 1
                                    conn.execute(
                                        """
                                        INSERT INTO quiz_versions(quiz_id, version_no, note_from_teacher, created_at)
                                        VALUES (?, ?, ?, ?)
                                        """,
                                        (q["id"], next_version, note, now_oman().isoformat()),
                                    )
                                    version_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                                    conn.execute(
                                        """
                                        UPDATE quizzes
                                        SET latest_version_no=?, status='submitted', updated_at=?
                                        WHERE id=?
                                        """,
                                        (next_version, now_oman().isoformat(), q["id"]),
                                    )
                                save_files(version_id, files2)
                                st.success("تم رفع النسخة المعدلة وإرسالها للمراجعة.")
                                st.rerun()

    with t3:
        with get_conn() as conn:
            notes = conn.execute(
                """
                SELECT * FROM notifications
                WHERE teacher_id=?
                ORDER BY created_at DESC
                """,
                (user["id"],),
            ).fetchall()

        if not notes:
            st.info("لا توجد إشعارات حاليًا.")
        else:
            for n in notes:
                st.write(f"**{n['title']}** — {n['message']} ({n['created_at'][:16]})")


def admin_dashboard(user):
    st.title(f"مرحبًا {user['full_name']}")
    st.caption("لوحة المشرف")

    t1, t2, t3, t4 = st.tabs(["لوحة التحكم", "المدارس والمعلمون", "مراجعة الاختبارات", "التقارير"])

    with t1:
        with get_conn() as conn:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status='submitted' OR status='in_review' THEN 1 ELSE 0 END) AS pending,
                    SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved,
                    SUM(CASE WHEN status='needs_revision' THEN 1 ELSE 0 END) AS revision,
                    SUM(CASE WHEN is_late=1 THEN 1 ELSE 0 END) AS late_count
                FROM quizzes
                """
            ).fetchone()
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("إجمالي", totals["total"] or 0)
        c2.metric("قيد المراجعة", totals["pending"] or 0)
        c3.metric("معتمد", totals["approved"] or 0)
        c4.metric("يحتاج تعديل", totals["revision"] or 0)
        c5.metric("متأخر", totals["late_count"] or 0)

    with t2:
        st.subheader("إدارة المدارس")
        new_school = st.text_input("اسم مدرسة جديدة")
        if st.button("إضافة مدرسة"):
            if new_school.strip():
                try:
                    with get_conn() as conn:
                        conn.execute(
                            "INSERT INTO schools(name, created_at) VALUES (?, ?)",
                            (new_school.strip(), now_oman().isoformat()),
                        )
                    st.success("تمت إضافة المدرسة.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("اسم المدرسة موجود مسبقًا.")

        with get_conn() as conn:
            schools = conn.execute("SELECT * FROM schools ORDER BY name").fetchall()
        st.write("المدارس:")
        for s in schools:
            st.write(f"- {s['name']}")

        st.subheader("إضافة معلم يدويًا")
        with st.form("create_teacher"):
            full_name = st.text_input("اسم المعلم")
            email = st.text_input("البريد الإلكتروني للمعلم")
            password = st.text_input("كلمة مرور مؤقتة", type="password")
            school_name = st.selectbox("المدرسة", options=[s["name"] for s in schools] if schools else [])
            submitted = st.form_submit_button("إضافة المعلم")

        if submitted:
            if not schools:
                st.error("أضف مدرسة أولاً.")
            elif not full_name or not email or not password:
                st.error("أكمل جميع الحقول.")
            else:
                school_id = next(s["id"] for s in schools if s["name"] == school_name)
                try:
                    with get_conn() as conn:
                        conn.execute(
                            """
                            INSERT INTO users(role, full_name, email, password_hash, school_id, created_at)
                            VALUES ('teacher', ?, ?, ?, ?, ?)
                            """,
                            (full_name.strip(), email.strip().lower(), hash_password(password), school_id, now_oman().isoformat()),
                        )
                    st.success("تمت إضافة المعلم.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("البريد الإلكتروني مستخدم مسبقًا.")

        st.subheader("استيراد معلمين من Excel")
        st.caption("الأعمدة المطلوبة: full_name, email, password, school_name")
        excel = st.file_uploader("ملف Excel", type=["xlsx"], key="teachers_excel")
        if st.button("استيراد", key="import_excel") and excel:
            df = pd.read_excel(excel)
            required = {"full_name", "email", "password", "school_name"}
            if not required.issubset(set(df.columns)):
                st.error("تنسيق الملف غير صحيح.")
            else:
                imported = 0
                failed = 0
                errors = []
                school_map = {s["name"]: s["id"] for s in schools}
                with get_conn() as conn:
                    for i, row in df.iterrows():
                        try:
                            school_id = school_map[str(row["school_name"]).strip()]
                            conn.execute(
                                """
                                INSERT INTO users(role, full_name, email, password_hash, school_id, created_at)
                                VALUES ('teacher', ?, ?, ?, ?, ?)
                                """,
                                (
                                    str(row["full_name"]).strip(),
                                    str(row["email"]).strip().lower(),
                                    hash_password(str(row["password"])),
                                    school_id,
                                    now_oman().isoformat(),
                                ),
                            )
                            imported += 1
                        except Exception as ex:
                            failed += 1
                            errors.append(f"Row {i + 2}: {ex}")
                st.success(f"تم الاستيراد: {imported} | فشل: {failed}")
                if errors:
                    st.code("\n".join(errors[:20]))

    with t3:
        with get_conn() as conn:
            school_opts = conn.execute("SELECT id, name FROM schools ORDER BY name").fetchall()
            teacher_opts = conn.execute("SELECT id, full_name FROM users WHERE role='teacher' ORDER BY full_name").fetchall()

        c1, c2, c3, c4 = st.columns(4)
        school_filter = c1.selectbox("المدرسة", ["الكل"] + [s["name"] for s in school_opts])
        teacher_filter = c2.selectbox("المعلم", ["الكل"] + [t["full_name"] for t in teacher_opts])
        status_filter = c3.selectbox("الحالة", ["الكل", "submitted", "in_review", "approved", "needs_revision"])
        late_filter = c4.selectbox("الرفع", ["الكل", "ضمن الوقت", "متأخر"])

        query = """
            SELECT q.*, u.full_name AS teacher_name, s.name AS school_name
            FROM quizzes q
            JOIN users u ON u.id=q.teacher_id
            JOIN schools s ON s.id=q.school_id
            WHERE 1=1
        """
        params = []
        if school_filter != "الكل":
            query += " AND s.name=?"
            params.append(school_filter)
        if teacher_filter != "الكل":
            query += " AND u.full_name=?"
            params.append(teacher_filter)
        if status_filter != "الكل":
            query += " AND q.status=?"
            params.append(status_filter)
        if late_filter == "ضمن الوقت":
            query += " AND q.is_late=0"
        elif late_filter == "متأخر":
            query += " AND q.is_late=1"

        query += " ORDER BY q.created_at DESC"
        with get_conn() as conn:
            quizzes = conn.execute(query, params).fetchall()

        if not quizzes:
            st.info("لا توجد نتائج.")
        else:
            for q in quizzes:
                st.markdown(
                    f"### اختبار #{q['id']} — {q['teacher_name']} ({q['school_name']}) "
                    f"<span class='pill {q['status']}'>{status_label(q['status'])}</span>",
                    unsafe_allow_html=True,
                )
                st.write(f"الصف: {q['grade_label']} | تاريخ التنفيذ: {q['execution_date']}")
                if q["is_late"]:
                    st.markdown("<span class='pill late'>رفع متأخر</span>", unsafe_allow_html=True)

                with get_conn() as conn:
                    versions = conn.execute(
                        "SELECT * FROM quiz_versions WHERE quiz_id=? ORDER BY version_no DESC",
                        (q["id"],),
                    ).fetchall()
                    latest = versions[0]
                    files = conn.execute(
                        "SELECT * FROM quiz_files WHERE quiz_version_id=?",
                        (latest["id"],),
                    ).fetchall()

                st.write(f"آخر نسخة: Version {latest['version_no']}")
                for f in files:
                    path = Path(f["storage_path"])
                    if path.exists():
                        st.download_button(
                            label=f"تحميل: {f['original_filename']}",
                            data=path.read_bytes(),
                            file_name=f["original_filename"],
                            key=f"dl_{f['id']}",
                        )

                note = st.text_area("ملاحظة المشرف الرسمية", key=f"admin_note_{q['id']}")
                col_a, col_b = st.columns(2)
                if col_a.button("اعتماد", key=f"approve_{q['id']}"):
                    if not note.strip():
                        st.error("أدخل ملاحظة رسمية قبل الاعتماد.")
                    else:
                        with get_conn() as conn:
                            conn.execute(
                                """
                                INSERT INTO quiz_reviews(quiz_id, quiz_version_id, reviewed_by_admin_id, decision, official_note, created_at)
                                VALUES (?, ?, ?, 'approved', ?, ?)
                                """,
                                (q["id"], latest["id"], user["id"], note.strip(), now_oman().isoformat()),
                            )
                            conn.execute(
                                "UPDATE quizzes SET status='approved', updated_at=? WHERE id=?",
                                (now_oman().isoformat(), q["id"]),
                            )
                        add_notification(q["teacher_id"], q["id"], "تم اعتماد الاختبار", note.strip())
                        st.success("تم اعتماد الاختبار وإرسال إشعار للمعلم.")
                        st.rerun()

                if col_b.button("طلب تعديل", key=f"revise_{q['id']}"):
                    if not note.strip():
                        st.error("أدخل ملاحظة رسمية لطلب التعديل.")
                    else:
                        with get_conn() as conn:
                            conn.execute(
                                """
                                INSERT INTO quiz_reviews(quiz_id, quiz_version_id, reviewed_by_admin_id, decision, official_note, created_at)
                                VALUES (?, ?, ?, 'needs_revision', ?, ?)
                                """,
                                (q["id"], latest["id"], user["id"], note.strip(), now_oman().isoformat()),
                            )
                            conn.execute(
                                "UPDATE quizzes SET status='needs_revision', updated_at=? WHERE id=?",
                                (now_oman().isoformat(), q["id"]),
                            )
                        add_notification(q["teacher_id"], q["id"], "الاختبار يحتاج تعديل", note.strip())
                        st.warning("تم إرسال طلب تعديل للمعلم.")
                        st.rerun()

    with t4:
        with get_conn() as conn:
            report = conn.execute(
                """
                SELECT u.full_name,
                       COUNT(q.id) AS total,
                       SUM(CASE WHEN q.status='approved' THEN 1 ELSE 0 END) AS approved,
                       SUM(CASE WHEN q.status='needs_revision' THEN 1 ELSE 0 END) AS needs_revision
                FROM users u
                LEFT JOIN quizzes q ON q.teacher_id=u.id
                WHERE u.role='teacher'
                GROUP BY u.id, u.full_name
                ORDER BY u.full_name
                """
            ).fetchall()

        if not report:
            st.info("لا توجد بيانات تقارير بعد.")
        else:
            df = pd.DataFrame([dict(r) for r in report])
            df["approval_rate"] = (df["approved"] / df["total"].replace(0, 1) * 100).round(1)
            st.dataframe(df, use_container_width=True)

            st.download_button(
                "تصدير Excel",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name="quiz_report.csv",
                mime="text/csv",
            )


if "user" not in st.session_state:
    login_view()
else:
    current = st.session_state.user
    with st.sidebar:
        st.write(f"**{current['full_name']}**")
        st.write("مشرف" if current["role"] == "admin" else "معلم")
        if st.button("تسجيل الخروج"):
            st.session_state.pop("user", None)
            st.rerun()

    if current["role"] == "admin":
        admin_dashboard(current)
    else:
        teacher_dashboard(current)
