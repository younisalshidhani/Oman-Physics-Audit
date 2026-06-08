require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');

const schoolsRouter = require('./src/routes/schools');
const teachersRouter = require('./src/routes/teachers');
const supervisorsRouter = require('./src/routes/supervisors');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// API routes
app.use('/api/schools', schoolsRouter);
app.use('/api/teachers', teachersRouter);
app.use('/api/supervisors', supervisorsRouter);

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', service: 'Edu-Registry API', timestamp: new Date().toISOString() });
});

// 404 for unknown API routes
app.use('/api', (req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

app.listen(PORT, () => {
  console.log(`Edu-Registry server running at http://localhost:${PORT}`);
});

module.exports = app;
