# Edu-Registry

سجلّ بيانات مركزي خفيف (MVP) للمدارس والمعلمين والمشرفين، يوفّر واجهة برمجية REST
للقراءة فقط وواجهة ويب تجريبية، مع تخزين مؤقت بصيغة JSON.

> **الحالة:** نموذج أولي للاختبار — وليس نظام إنتاج. لا مصادقة ولا صلاحيات في هذا الإصدار (مقصود).

## النطاق والعلاقة بنظام نوب (مهم)
هذا المشروع **منفصل تمامًا** عن نظام **نوب** (NOOB):
- **نوب** يحلّ مشكلة *توزيع حصص المعلمين البدلاء* (نظام full-stack، PostgreSQL، محرك مطابقة).
- **Edu-Registry** يحلّ مشكلة *سجلّ بيانات مركزي* (مدارس/معلمون/مشرفون) كـ **تطبيق ويب مستقل قائم بذاته**، غير مرتبط بأي منظومة خارجية.

لا تخلط بين المستودعين رغم تشابه السياق التعليمي. الأسماء والأهداف والبنى مختلفة.

## التقنيات
Node.js + Express · CORS · dotenv · تخزين JSON (مرحلة MVP) · واجهة HTML بسيطة

## هيكل المشروع
```
edu-registry/
├── server.js                       # نقطة تشغيل الخادم
├── package.json
├── .env.example
├── .gitignore
├── README.md
├── src/
│   ├── routes/                     # نقاط الـ API
│   │   ├── schools.js
│   │   ├── teachers.js
│   │   └── supervisors.js
│   ├── repositories/
│   │   └── repository.js           # طبقة تجريد التخزين (تعزل مصدر البيانات)
│   ├── data/                       # بيانات JSON
│   │   ├── schools.json
│   │   ├── teachers.json
│   │   └── supervisors.json
│   └── utils/
│       └── dataLoader.js           # قراءة ملفات JSON
└── public/
    └── index.html                  # واجهة الاختبار
```

## التشغيل
```bash
npm install
cp .env.example .env   # اختياري لضبط PORT
npm start
```
ثم افتح: http://localhost:3000

## نقاط الـ API
| الطريقة | المسار            | الوصف              |
|--------|-------------------|--------------------|
| GET    | /api/schools      | قائمة المدارس       |
| GET    | /api/teachers     | قائمة المعلمين      |
| GET    | /api/supervisors  | قائمة المشرفين      |
| GET    | /api/health       | فحص حالة الخادم     |

## نماذج البيانات
```json
// School
{ "schoolname": "Al Amal School", "wilayat": "Muscat" }
// Teacher
{ "teachername": "Ahmed Al-Balushi", "major": "Physics", "schoolname": "Al Amal School" }
// Supervisor
{ "name": "Supervisor A", "schoolname": "Al Amal School" }
```

## قيد جوهري في طبقة التخزين
تخزين JSON آمن **للقراءة فقط**. أي عملية كتابة متزامنة (CRUD) على ملف مسطّح
عرضة لتعارض الكتابات وفقدان البيانات (race conditions)، لعدم وجود أقفال أو معاملات.
لذلك عمليات الإنشاء/التعديل/الحذف **غير مُنفّذة عمدًا**، وتجريد التخزين معزول في
`src/repositories/repository.js` بحيث يكون الانتقال لقاعدة بيانات تعديلًا في ملف واحد.

## خارطة التطوير
1. CRUD كامل **بعد** الانتقال لقاعدة بيانات (لا فوق JSON)
2. قاعدة بيانات (PostgreSQL / MongoDB)
3. المصادقة (JWT — Admin/Supervisor/Teacher)
4. لوحة تحكم (React / Next.js)
5. بحث وتصفية في الواجهة + تصدير CSV/JSON
6. نموذج SaaS متعدد المدارس

## الترخيص
MIT — للاستخدام التعليمي والتطويري.
