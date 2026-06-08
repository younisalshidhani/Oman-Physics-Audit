const express = require('express');
const router = express.Router();
const { teachersRepo } = require('../repositories/repository');

// GET /api/teachers — return list of teachers
router.get('/', (req, res) => {
  res.json(teachersRepo.getAll());
});

module.exports = router;
