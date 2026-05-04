# LegalSheild AI

## Overview

LegalAI (LegalShield AI Brain) is an intelligent legal document analysis platform designed to demystify complex contracts for non-lawyers. It identifies risky legal clauses, translates legalese into plain English ("ELI5" mode), assigns risk scores, and provides negotiation guidance—helping users understand and negotiate contracts confidently.

This project combines machine learning with natural language processing to analyze uploaded PDF contracts, extract key clauses, assess risks, and offer actionable insights. Built with a FastAPI backend for robust API handling and a modern React frontend for an intuitive user experience.

## Features

- **PDF Upload & Text Extraction**: Supports PDF uploads with multiple extraction methods (OCR via Tesseract, PyPDF, PyMuPDF) for reliable text parsing.
- **Risk Assessment**: Dual-scoring system using regex pattern matching and a trained Random Forest ML model to evaluate contract risk on a 0-100 scale.
- **Clause Analysis**: Identifies over 50 common legal clauses (e.g., indemnification, arbitration, non-compete) with risk ratings.
- **ELI5 Mode**: Translates complex legal terms into simple, emoji-enhanced explanations for accessibility.
- **Negotiation Toolkit**: Provides counter-proposal suggestions and negotiation strategies based on identified risks.
- **Interactive UI**: Drag-and-drop interface, animated risk gauge, dual-view explanations, and compliance checklists.
- **Report Export**: Generate professional PDF reports of analysis results using jsPDF.
- **Entity Extraction**: Identifies parties, deadlines, and payment terms.
- **Auto-Training**: Backend automatically trains ML models if not present at startup.

## Technologies Used

### Backend
- **Python 3.x**
- **FastAPI**: High-performance web framework for REST API.
- **scikit-learn**: Machine learning library for model training and prediction.
- **pandas**: Data manipulation and analysis.
- **joblib**: Model serialization.
- **pytesseract**: OCR for text extraction from images.
- **PyPDF2 / PyMuPDF**: PDF text extraction.
- **python-multipart**: File upload handling.

### Frontend
- **React 19.2.5**: JavaScript library for building user interfaces.
- **Vite**: Fast build tool and development server.
- **Tailwind CSS 4.2.4**: Utility-first CSS framework.
- **Framer Motion**: Animation library.
- **lucide-react**: Icon library.
- **jsPDF**: PDF generation for reports.
- **canvas-confetti**: Celebration animations.

### ML/Data
- **Random Forest Classifier**: Supervised learning model for risk prediction.
- **TF-IDF Vectorizer**: Text feature extraction.
- **Synthetic Dataset Generation**: Custom scripts for training data.

## Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- Git

### Setup Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/hansagusaiwal/LegalShield-AI.git
   cd LegalAI
   ```

2. **Run the Startup Script** (Windows PowerShell):
   - Execute `start.ps1` to install dependencies, generate data, train models, and launch the application.
   - This script installs Python and Node.js dependencies, generates a synthetic legal dataset, trains the ML model, and starts both backend (port 8000) and frontend (port 3000).

   Alternatively, manual setup:
   - **Backend**:
     ```bash
     cd backend
     pip install fastapi uvicorn pandas scikit-learn joblib pytesseract pillow python-multipart
     ```
   - **Frontend**:
     ```bash
     cd frontend
     npm install
     ```
   - **Data & Model**:
     ```bash
     cd scripts
     python generate_data.py
     cd ../model
     python train_model.py
     ```

3. **Launch the Application**:
   - Backend: `uvicorn main:app --reload` (from `backend/` directory)
   - Frontend: `npm start` (from `frontend/` directory)
   - Access the app at `http://localhost:3000`

## Usage

1. Open the frontend in your browser.
2. Drag and drop a PDF contract file into the upload area.
3. View the risk gauge and analysis results.
4. Toggle between standard legal explanations and ELI5 mode.
5. Review identified clauses, negotiation tips, and checklists.
6. Export a PDF report of the analysis.

### API Endpoints
- `POST /upload`: Upload a PDF file for analysis. Returns JSON with risk score, clauses, and insights.

## Project Structure

```
LegalAI/
├── start.ps1                 # Startup script for Windows
├── backend/
│   ├── main.py               # FastAPI server and analysis logic
│   ├── output.json           # Sample API response
│   ├── pdf_text_utf8.txt     # Extracted text samples
│   └── pdf_text.txt
├── data/
│   └── legal_data.csv        # Training dataset
├── frontend/
│   ├── package.json          # Node.js dependencies
│   ├── index.html            # Main HTML file
│   ├── vite.config.js        # Vite configuration
│   ├── tailwind.config.js    # Tailwind CSS config
│   ├── postcss.config.js     # PostCSS config
│   ├── eslint.config.js      # ESLint config
│   ├── README.md             # Frontend-specific README
│   ├── public/               # Static assets
│   └── src/
│       ├── main.jsx          # React entry point
│       ├── App.jsx           # Main React component
│       ├── App.css           # Styles
│       ├── index.css         # Global styles
│       └── assets/           # Images and icons
├── model/
│   ├── train_model.py        # ML model training script
│   ├── train_v2.py           # Alternative training
│   ├── train.py              # Basic training
│   ├── generate_dataset.py   # Dataset generation
│   ├── legal_brain.joblib    # Trained model
│   ├── legal_model.joblib    # Model file
│   ├── legal_risk_model.joblib # Risk model
│   ├── tfidf_vectorizer.joblib # Vectorizer
│   └── vectorizer.joblib     # Additional vectorizer
└── scripts/
    └── generate_data.py      # Data generation script
```

## Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a feature branch: `git checkout -b feature-name`.
3. Commit changes: `git commit -m 'Add feature'`.
4. Push to the branch: `git push origin feature-name`.
5. Open a pull request.

Ensure code follows the existing style and includes tests where applicable.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contact

For questions or support, please open an issue on GitHub or contact the maintainers.
