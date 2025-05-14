🐾 Veterinary Blood Test Analyzer – FastAPI Backend
A scalable and maintainable FastAPI-based backend for analyzing veterinary blood test PDFs. This service extracts pages from PDFs, converts them into high-resolution images, and supports modular routing for further analysis.

🚀 Project Overview
This project powers a veterinary diagnostics platform through:

FastAPI-based RESTful API for PDF analysis

Modular architecture for maintainability and scalability

High-resolution PDF-to-image conversion

Centralized logging for visibility and debugging

🔑 Key Features
⚙️ FastAPI Backend
Provides RESTful endpoints for handling diagnostic workflows

Modular routing (analysis_router)

Rich metadata: title, version, description

Graceful error handling with log traces

🖼 PDF-to-Image Conversion
Converts multi-page PDFs into high-resolution PNGs (300 DPI)

Built with PyMuPDF (fitz)

Returns a list of image paths for downstream processing

🧾 Logging
Centralized logging with a custom Logger utility

Tracks app initialization, PDF conversion steps, and exception traces

📁 File-by-File Breakdown
requirements.txt
Specifies all dependencies. Key libraries include:

fastapi – Core API framework

uvicorn – ASGI server

PyMuPDF – For PDF rendering

pydantic – Input validation

colorama – Colored logs in terminal

app/main.py
Purpose: Application entrypoint and FastAPI initialization

Creates FastAPI instance with metadata

Includes modular analysis_router

Sets up initial logger

Handles exceptions during startup gracefully

app/utils/file_utils.py
Purpose: PDF to Image conversion logic

FileConverter.convert_pdf_to_image_list()

Converts each PDF page to a uniquely named PNG at 300 DPI

Handles multi-page PDFs efficiently

Returns a list of output file paths

Logs errors during PDF access or image generation

app/utils/logger_utils.py (assumed)
Purpose: Centralized logging utility

Configures logging format and levels

Ensures consistent logging across modules

✅ Strengths
🧩 Modular Design: Routing, utilities, and logging are separated

💥 Robust Error Handling: Logs and handles all critical issues

📈 Scalable: Supports large PDFs, multiple endpoints, and growth

📌 Status
🛠 In active development. Prototype-ready and extendable.