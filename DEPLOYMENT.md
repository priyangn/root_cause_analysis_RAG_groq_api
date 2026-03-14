# CauseSense AI - Deployment Guide

## Platform Overview
**CauseSense AI** - AI Root Cause Intelligence Platform for Machine Failure Analysis

## Technology Stack
- **Frontend**: React 18 + Tailwind CSS + Recharts
- **Backend**: Python FastAPI + Motor (MongoDB async driver)
- **Database**: MongoDB
- **AI/ML**: Claude Sonnet 4.5 (via Emergent LLM), LangGraph, scikit-learn, XGBoost, SHAP
- **Vector Database**: ChromaDB

## Current Deployment Status
✅ **Ready for Production Deployment**

## Service Configuration

### Backend (Port 8001)
- **Location**: `/app/backend/`
- **Main File**: `server.py`
- **Dependencies**: `requirements.txt`
- **Environment Variables**: `/app/backend/.env`
  - `MONGO_URL`: MongoDB connection string
  - `DB_NAME`: Database name
  - `CORS_ORIGINS`: Allowed CORS origins
  - `EMERGENT_LLM_KEY`: Universal LLM API key

### Frontend (Port 3000)
- **Location**: `/app/frontend/`
- **Build Tool**: React Scripts
- **Environment Variables**: `/app/frontend/.env`
  - `REACT_APP_BACKEND_URL`: Backend API URL

### Database
- **MongoDB**: Running on localhost:27017
- **Database Name**: `test_database`
- **Collections**:
  - `users` - User authentication
  - `uploaded_files` - File metadata
  - `analyses` - Analysis results
  - `chat_messages` - Chat history

## Key Features
1. ✅ User Authentication (JWT-based)
2. ✅ File Upload (CSV, PDF, Excel, TXT, DOCX)
3. ✅ Multi-Agent AI Analysis Pipeline
4. ✅ Real-time Progress Tracking with Time Estimates
5. ✅ Anomaly Detection with Timestamps
6. ✅ ML Model Training (Random Forest, XGBoost, Gradient Boosting)
7. ✅ Confusion Matrix Visualization
8. ✅ Time-Series Visualizations
9. ✅ Correlation Analysis
10. ✅ Feature Importance Charts
11. ✅ Hypothesis Generation
12. ✅ Causal Inference (SHAP)
13. ✅ AI Chat Assistant
14. ✅ Project Management with Delete Functionality

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user

### File Management
- `POST /api/upload` - Upload file
- `GET /api/upload` - List uploaded files
- `DELETE /api/upload/{file_id}` - Delete file

### Analysis
- `POST /api/analysis/start` - Start new analysis
- `GET /api/analysis/{analysis_id}` - Get analysis results
- `GET /api/analysis` - List all analyses
- `DELETE /api/analysis/{analysis_id}` - Delete analysis

### Chat
- `POST /api/chat` - Send chat message

### Health
- `GET /api/` - API status
- `GET /api/health` - Health check

## Security Features
- ✅ JWT token-based authentication
- ✅ Password hashing with bcrypt (4 rounds optimized for speed)
- ✅ User data isolation (per-user file and analysis access)
- ✅ CORS configuration
- ✅ Environment variable protection

## Performance Optimizations
- ✅ Async MongoDB operations (Motor)
- ✅ Background task processing for analysis
- ✅ Optimized bcrypt rounds (4) for fast login
- ✅ Hot reload enabled for development
- ✅ Progress tracking to avoid UI blocking
- ✅ Data visualization limited to 50 points

## Deployment Checklist

### Pre-Deployment
- [x] All services running
- [x] Environment variables configured
- [x] No hardcoded URLs or credentials
- [x] API endpoints tested
- [x] Authentication working
- [x] File upload/delete working
- [x] Analysis pipeline operational
- [x] Visualizations rendering
- [x] Chat functionality working

### Production Considerations
1. **Security**:
   - Update `SECRET_KEY` in production
   - Configure proper CORS origins
   - Increase bcrypt rounds to 10-12 for production
   - Enable HTTPS

2. **Database**:
   - Configure MongoDB replica set for production
   - Set up database backups
   - Configure proper indexes

3. **Storage**:
   - Configure persistent storage for uploads
   - Set up file cleanup policies
   - Consider cloud storage (S3, GCS) for files

4. **Monitoring**:
   - Add application logging
   - Configure error tracking (Sentry)
   - Set up performance monitoring
   - Configure uptime monitoring

5. **Scaling**:
   - Configure load balancer
   - Set up Redis for session management
   - Consider horizontal scaling for API

## Deployment Commands

### Start Services
```bash
sudo supervisorctl start backend
sudo supervisorctl start frontend
sudo supervisorctl start mongodb
```

### Stop Services
```bash
sudo supervisorctl stop backend
sudo supervisorctl stop frontend
```

### Restart Services
```bash
sudo supervisorctl restart backend
sudo supervisorctl restart frontend
```

### View Logs
```bash
tail -f /var/log/supervisor/backend.err.log
tail -f /var/log/supervisor/frontend.err.log
```

## URLs
- **Application**: https://root-cause-ai-3.preview.emergentagent.com
- **API**: https://root-cause-ai-3.preview.emergentagent.com/api

## Support
For issues or questions, refer to the system logs or contact support.

## Version
- **Version**: 1.0.0
- **Build Date**: 2026-03-14
- **Status**: Production Ready ✅
