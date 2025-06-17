# 🐾 Veterinary Bloodwork Analyzer - FastAPI Backend

A production-ready, object-oriented FastAPI backend for analyzing veterinary blood test PDFs using AI-powered vision models. This system provides comprehensive bloodwork analysis with structured medical reports following veterinary diagnostic standards.

## 🚀 Project Overview

This application processes veterinary PDF bloodwork reports through an intelligent workflow:

1. **PDF Upload & Validation** - Accepts and validates PDF blood test reports
2. **High-Resolution Conversion** - Converts PDFs to 300 DPI images for optimal analysis
3. **AI-Powered Analysis** - Uses OpenAI's GPT-4o vision model for comprehensive interpretation
4. **Structured Medical Reports** - Generates detailed JSON reports with diagnostic insights
5. **Background Processing** - Non-blocking analysis with UUID-based result retrieval

## 🏗️ Architecture

The application follows **Clean Architecture** principles with clear separation of concerns:

```
app/
├── main.py                    # Application entry point & FastAPI configuration
├── routers/                   # API endpoints and request handling
│   └── analysis_router.py     # PDF analysis endpoints
├── services/                  # Business logic and external integrations
│   ├── pdf_analysis_service.py    # Core PDF processing workflow
│   ├── openai_service.py          # AI analysis integration
│   └── vision_model_inference_service.py  # Alternative inference service
└── utils/                     # Shared utilities and helpers
    ├── file_utils.py          # PDF/image processing utilities
    ├── logger_utils.py        # Centralized logging system
    └── ec2_instance_controller.py  # AWS infrastructure management
```

## 🔑 Key Features

### ⚙️ Object-Oriented Design

- **Single Responsibility Principle**: Each class has one clear responsibility
- **Dependency Injection**: Clean separation between components
- **Encapsulation**: Private methods and proper data hiding
- **Inheritance**: Legacy compatibility while encouraging new patterns

### 🖼️ Advanced File Processing

- **High-Resolution PDF Conversion**: 300 DPI PNG output using PyMuPDF
- **Multi-Page Support**: Handles complex multi-page blood test reports
- **Robust Error Handling**: Comprehensive exception management with logging
- **Memory Efficient**: Proper resource cleanup and temporary file management

### 🤖 AI-Powered Analysis

- **GPT-4o Vision Integration**: State-of-the-art medical image analysis
- **Comprehensive Medical Reports**: 15+ analysis sections including:
  - Patient information extraction
  - Parameter analysis with reference ranges
  - Mathematical ratio calculations (BUN/Creatinine, Na/K, etc.)
  - Clinical interpretation with differential diagnoses
  - Urgency classification (EMERGENCY/URGENT/ROUTINE)
  - Treatment recommendations and follow-up plans
- **Italian Language Support**: Medical terminology in Italian
- **Structured JSON Output**: Consistent, parseable medical reports

### 📊 Professional Logging

- **Centralized Logger**: Application-wide consistent logging
- **Module-Specific Loggers**: Granular tracking by component
- **Structured Format**: Timestamped, leveled log messages
- **Error Tracking**: Comprehensive exception logging with stack traces

### ☁️ Cloud Integration

- **AWS EC2 Management**: Automated inference server startup and monitoring
- **Instance Health Checking**: System and instance status validation
- **Timeout Handling**: Robust startup sequence with configurable timeouts

## 📋 Requirements

### System Requirements

- **Python 3.11+**
- **AWS Account** (for EC2 features)
- **OpenAI API Key** with GPT-4o access

### Python Dependencies

```txt
fastapi==0.115.12          # Modern async web framework
uvicorn==0.34.2            # ASGI server
PyMuPDF==1.26.0            # High-quality PDF processing
openai==1.84.0             # OpenAI API integration
boto3==1.38.27             # AWS services integration
httpx==0.28.1              # Async HTTP client
pydantic==2.11.4           # Data validation
requests==2.32.3           # HTTP library
python-multipart==0.0.20   # File upload support
python-dotenv==0.9.9       # Environment variable management
```

## 🛠️ Installation & Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd bloodwork-backend
```

### 2. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
```

### 4. Directory Structure

The application will automatically create necessary directories:

```
data/
└── blood_work_pdfs/     # Analysis results storage
    └── {uuid}/          # Individual analysis sessions
        ├── {uuid}_page_1.png    # Converted images
        ├── {uuid}_page_2.png
        └── model_output.json    # AI analysis results
```

## 🚀 Running the Application

### Development Mode

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/analysis/

## 📡 API Endpoints

### POST /analysis/pdf_analysis

Upload and analyze a veterinary PDF bloodwork report.

**Request:**

```bash
curl -X POST "http://localhost:8000/analysis/pdf_analysis" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@bloodwork_report.pdf"
```

**Response:**

```json
{
  "pdf_uuid": "12345678-1234-1234-1234-123456789012",
  "message": "Analisi in corso. Torna più tardi per vedere i risultati."
}
```

### GET /analysis/pdf_analysis_result/{uuid}

Retrieve analysis results by UUID.

**Request:**

```bash
curl "http://localhost:8000/analysis/pdf_analysis_result/12345678-1234-1234-1234-123456789012"
```

**Response (Ready):**

```json
{
  "paziente": {
    "nome": "CAPPUCCIO",
    "specie": "GATTO",
    "eta": "12 anni",
    "sesso": "Maschio"
  },
  "parametri": [
    {
      "parametro": "RBC",
      "valore": "6.82",
      "unita": "milioni/µL",
      "range": "5.00 - 10.00",
      "stato": "normale"
    }
  ],
  "interpretazione_clinica": {
    "diagnosi_differenziali": [
      {
        "diagnosi": "Neoplasia maligna",
        "confidenza": "70%"
      }
    ]
  }
}
```

**Response (Processing):**

```json
{
  "detail": "Risultato non ancora pronto"
}
```

## 🏛️ Code Architecture Details

### Design Patterns Used

1. **Dependency Injection Pattern**

   ```python
   class BloodworkPdfAnalysisService:
       def __init__(self):
           self._pdf_converter = PdfImageConverter()
           self._ai_service = BloodworkAnalysisService()
   ```

2. **Factory Pattern**

   ```python
   class ApplicationLogger:
       @classmethod
       def get_logger(cls, module_name: str) -> logging.Logger:
           return cls._logger.getChild(module_name)
   ```

3. **Strategy Pattern**
   ```python
   # Different AI services can be swapped
   class BloodworkAnalysisService: ...      # OpenAI implementation
   class RemoteVisionInferenceService: ...  # Custom inference server
   ```

### Error Handling Strategy

The application uses a **three-tier error handling approach**:

1. **Service Level**: Catch and log specific errors, raise meaningful exceptions
2. **Router Level**: Handle HTTP-specific errors, return proper status codes
3. **Application Level**: Global exception handlers for unhandled errors

```python
# Example: Service level error handling
try:
    result = await self._ai_service.analyze_bloodwork_images(image_paths)
except Exception as error:
    self._logger.exception(f"AI analysis failed: {error}")
    raise RuntimeError("AI analysis failed") from error
```

### Configuration Management

Each service uses a dedicated configuration class:

```python
class PdfAnalysisConfiguration:
    def __init__(self):
        self.uploads_root_directory = Path("data/blood_work_pdfs")
        self.model_output_filename = "model_output.json"
        self.supported_content_type = "application/pdf"
```

## 🧪 Testing

### Manual Testing

```bash
# Test PDF upload
curl -X POST "http://localhost:8000/analysis/pdf_analysis" \
     -F "file=@test_bloodwork.pdf"

# Test result retrieval
curl "http://localhost:8000/analysis/pdf_analysis_result/{uuid}"
```

### Health Checks

```bash
# Application health
curl "http://localhost:8000/docs"

# Logger test
tail -f logs/application.log
```

## 🔧 Configuration Options

### Environment Variables

```env
# Required
OPENAI_API_KEY=sk-...                    # OpenAI API key

# Optional AWS Configuration
AWS_ACCESS_KEY_ID=AKIA...               # AWS access key
AWS_SECRET_ACCESS_KEY=...               # AWS secret key
AWS_DEFAULT_REGION=eu-north-1           # AWS region
```

### Application Settings

```python
# Modify in respective configuration classes
PDF_UPLOADS_ROOT_DIRECTORY = "data/blood_work_pdfs"
MODEL_OUTPUT_FILENAME = "model_output.json"
DEFAULT_DPI = 300
AI_REQUEST_TIMEOUT = 300  # seconds
```

## 📊 Monitoring & Logging

### Log Levels

- **INFO**: Normal operations, request tracking
- **WARNING**: Non-critical issues, fallback operations
- **ERROR**: Service failures, API errors
- **EXCEPTION**: Full stack traces for debugging

### Log Format

```
2025-06-17 10:30:45,123 - bloodwork_analyzer.pdf_analysis_service - INFO - Starting PDF analysis for: report.pdf (UUID: 12345...)
```

### Key Metrics to Monitor

- PDF upload success rate
- AI analysis completion time
- Error rates by service
- Memory usage during PDF processing
- Background task queue length

## 🚨 Troubleshooting

### Common Issues

1. **"OPENAI_API_KEY environment variable is required"**

   - Solution: Add your OpenAI API key to `.env` file

2. **"Failed to open PDF document"**

   - Solution: Ensure PDF is not corrupted and has read permissions

3. **"AI analysis failed"**

   - Check OpenAI API quota and internet connectivity
   - Verify image files were created successfully

4. **"EC2 instance did not start in time"**
   - Check AWS credentials and region configuration
   - Verify instance ID exists and has proper permissions

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload --log-level debug
```

## 🤝 Contributing

### Code Style Guidelines

- Follow **PEP 8** Python style guide
- Use **type hints** for all function parameters and returns
- Write **comprehensive docstrings** following Google style
- Implement **error handling** for all external dependencies
- Add **logging** for all major operations

### Adding New Features

1. Create feature branch: `git checkout -b feature/new-analysis-type`
2. Implement using existing patterns (OOP classes, dependency injection)
3. Add comprehensive error handling and logging
4. Update documentation
5. Submit pull request with detailed description

## 📄 License

This project is proprietary software developed for veterinary diagnostics.

## 🆘 Support

For technical support or questions:

- Check application logs first
- Review API documentation at `/docs`
- Contact development team with specific error messages and logs

---

**Built with ❤️ for veterinary professionals**

_This system is designed to assist veterinary diagnostics but should not replace professional medical judgment._
