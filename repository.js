const { loadData } = require('../utils/dataLoader');

/**
 * طبقة تجريد التخزين (Repository Pattern).
 *
 * بقية التطبيق تتحدث مع هذه الواجهة — لا مع الملفات مباشرةً.
 * اليوم تقرأ من ملفات JSON. للانتقال لقاعدة بيانات حقيقية لاحقًا
 * (PostgreSQL/MongoDB — المرحلة 2 في الخارطة) تعدّل هذا الملف فقط،
 * وتبقى المسارات (routes) دون تغيير.
 *
 * تنبيه بشأن الكتابة: getAll() للقراءة فقط وآمنة.
 * عمليات create/update/delete غير مُنفّذة عمدًا على JSON، لأن
 * الكتابة المتزامنة على ملف مسطّح غير آمنة معاملاتيًا (race conditions /
 * فقدان تحديثات). نفّذها فقط بعد الانتقال لقاعدة بيانات فعلية.
 */
function createRepository(filename) {
  return {
    getAll() {
      return loadData(filename);
    }
    // مستقبلًا (يتطلب قاعدة بيانات حقيقية):
    // create(record) {...}
    // update(id, patch) {...}
    // remove(id) {...}
  };
}

const schoolsRepo = createRepository('schools.json');
const teachersRepo = createRepository('teachers.json');
const supervisorsRepo = createRepository('supervisors.json');

module.exports = { createRepository, schoolsRepo, teachersRepo, supervisorsRepo };
