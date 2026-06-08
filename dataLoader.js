const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');

/**
 * Load and parse a JSON data file from src/data.
 * @param {string} filename - e.g. 'schools.json'
 * @returns {Array|Object} parsed JSON content, or [] on error
 */
function loadData(filename) {
  const filePath = path.join(DATA_DIR, filename);
  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    return JSON.parse(raw);
  } catch (err) {
    console.error(`Failed to load ${filename}:`, err.message);
    return [];
  }
}

module.exports = { loadData };
