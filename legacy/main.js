const express = require('express');
const cors = require('cors');
const fs = require('fs');
const csv = require('csv-parser');

const app = express();
const PORT = 5000;

app.use(cors());
app.use(express.json()


);

let medicalData = [];

// CSV file load kora hochhe
fs.createReadStream('medicine_data.csv')
  .pipe(csv())
  .on('data', (row) => {
    medicalData.push(row);
  })
  .on('end', () => {
    console.log('✅ Medicine Database Loaded Successfully!');
  });

// Search API
app.get('/api/search', (req, res) => {
    const query = req.query.name ? req.query.name.toLowerCase().trim() : "";
    const result = medicalData.find(item => item.Medicine && item.Medicine.toLowerCase() === query);
    
    if (result) {
        res.json({ status: "success", ...result });
    } else {
        res.json({ status: "not_found" });
    }
});

// Chatbot API
app.get('/api/chat', (req, res) => {
    const msg = req.query.message ? req.query.message.toLowerCase().trim() : "";
    const result = medicalData.find(item => item.Symptom && msg.includes(item.Symptom.toLowerCase()));
    
    if (result) {
        res.json({ status: "success", ...result });
    } else {
        res.json({ status: "not_found" });
    }
});

app.listen(PORT, () => {
    console.log(`🚀 NeuroCure+ Server running at http://localhost:${PORT}`);
});