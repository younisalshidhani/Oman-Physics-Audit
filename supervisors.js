const express = require('express');
const router = express.Router();
const { supervisorsRepo } = require('../repositories/repository');

// GET /api/supervisors — return list of supervisors
router.get('/', (req, res) => {
  res.json(supervisorsRepo.getAll());
});

module.exports = router;
