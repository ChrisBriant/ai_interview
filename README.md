# AI Interview Question Generator

## Overview

This project provides an **AI-powered system to generate interview questions** from job descriptions. It produces technical, architecture, scenario, and behavioral questions and stores them in a PostgreSQL database.  

It also supports a **FastAPI endpoint** to create job roles and question sets directly from JSON or raw job descriptions.

---

## Features

- Automatically generate interview questions for any job role.
- Categorizes questions into:
  - Technical
  - Architecture
  - Scenario
  - Behavioral
- Stores job roles and questions in a database for future reference.
- Supports async operations for scalable, high-performance processing.
- Includes a file-based pipeline for managing AI outputs and processing status:
  - `out/` – temporary storage for AI outputs
  - `processed/` – successfully stored JSON
  - `failed/` – optional folder for errors

---

## Usage

- Submit a job description to the API to generate questions.
- The system returns a structured JSON with all question types and the job description included.
- Generated JSON can be stored in the database and/or processed for further use.
- Successfully processed files are moved to the `processed` folder for organization.

---

## AI Integration

- Uses OpenAI models to generate structured interview questions.
- Ensures that job descriptions are included in the output JSON.
- Supports multiple categories of questions for comprehensive interview preparation.

---

## File Pipeline

- Job descriptions are processed by the AI to generate JSON outputs.
- Outputs are temporarily stored in `out/`.
- Once processed and inserted into the database, files are moved to `processed/`.
- Any failed or invalid files can be stored separately for review.

---

## License

MIT License © 2026

---

## Running

uvicorn main:app --host 0.0.0.0 --port 8000 --reload