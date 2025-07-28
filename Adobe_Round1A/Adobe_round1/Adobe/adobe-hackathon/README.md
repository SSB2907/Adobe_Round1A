#Challenge 1A: PDF Heading Extraction Tool

## Overview

This project is the official submission for **Challenge 1A** of the Adobe India Hackathon 2025.

The goal is to extract a **structured JSON outline** from a given PDF, including:
- The **title** of the document
- A hierarchical list of headings at levels **H1**, **H2**, and **H3**

The solution is designed to be:
- ⚡ **Fast** — Executes under **10 seconds** for a 50-page PDF
- 📦 **Offline** — Fully Dockerized and requires **no internet access**
- 💻 **Portable** — Compatible with **CPU-only (amd64)** architecture
- 🌐 **Multilingual** — Supports English, Hindi, Marathi, and other Indic languages
- ✅ **Constraint-Compliant** — Outputs clean, valid JSON in required format

---

## Project Structure

Challenge_1a/
├── input/
│ └── sample.pdf
├── output/
│ └── sample.json
├── extractor.py
├── Dockerfile
├── requirements.txt
└── README.md
---

## Task

Given a PDF file, extract a structured JSON outline with heading hierarchy and metadata.


### Sample Output Format

```json
{
  "title": "A Culinary Journey Through the South of France",
  "outline": [
    {
      "level": "H1",
      "text": "A Culinary Journey Through the South of France",
      "page": 0
    },
    {
      "level": "H1",
      "text": "Introduction",
      "page": 0
    },
    {
      "level": "H1",
      "text": "Types of Food",
      "page": 1
    },
    {
      "level": "H1",
      "text": "Seafood: With its extensive coastline, the South of France oﬀers an abundance of fresh",
      "page": 1
    },
    {
      "level": "H1",
      "text": "The cuisine in the South of France is diverse, reflecting the region's rich history and cultural",
      "page": 1
    },
    {
      "level": "H1",
      "text": "Famous Dishes",
      "page": 2
    },
  ]
}
```

How It Works
The script uses PyMuPDF (fitz) for parsing PDFs and applies a rule-based confidence scoring mechanism:
Font size analysis
Boldness detection
Top-of-page placement
Indic script detection (Devanagari, Tamil, etc.)
Span count (multi-line vs single-line detection)
Headings are assigned confidence scores and classified into H1, H2, and H3 levels using dynamic thresholds. A fallback mechanism handles low-information PDFs.


Libraries Used
PyMuPDF (fitz)

re, json, os, time, concurrent.futures

No internet-dependent or heavy ML libraries used


Docker Setup
Build the Docker Image
docker build -t heading-extractor:adobe .

Run the Extractor
Make sure your PDF files are placed inside the input/ directory.
On Linux/macOS/WSL
docker run --rm \
  -v "$(pwd)/input":/app/input \
  -v "$(pwd)/output":/app/output \
  heading-extractor:adobe

On Windows PowerShell
 docker run --rm `
   -v "${PWD}\input:/app/input" `
   -v "${PWD}\output:/app/output" `
    heading-extractor:adobe


Input/Output Format
Input:
Folder: /app/input
Files: One or more .pdf files (≤ 50 pages each)

Output:
Folder: /app/output
File(s): <filename>.json with heading structure

Example
Input: input/Devi_Aarti.pdf
Output:
{
  "title": "देवीच्या आरत्या",
  "outline": [
    { "level": "H1", "text": "देवीच्या आरत्या", "page": 0 },
    { "level": "H3", "text": "दुगाज देवीची आरती", "page": 1 },
    { "level": "H3", "text": "संतोषी मातेची आरती", "page": 2 }
  ]
}

Constraints Satisfied
Constraint	Status
Run time ≤ 10 sec / 50 pages✅
No internet access	✅
Runs on CPU (amd64)	✅
Model size ≤ 200MB (none used)✅
Output JSON format correct✅
Multilingual support✅


Notes
Make sure the input/ and output/ directories exist before running the container.