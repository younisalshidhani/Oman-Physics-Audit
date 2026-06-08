const express = require('express');
const router = express.Router();
const { schoolsRepo } = require('../repositories/repository');

// GET /api/schools — return list of schools
router.get('/', (req, res) => {
  res.json(schoolsRepo.getAll());
});

module.exports = router;
