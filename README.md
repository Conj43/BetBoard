<div align="center">
  <img src="betboard.png" alt="BetBoard Logo" width="200">
  <h1>BetBoard</h1>
</div>

A SwiftUI-based iOS application for tracking sports betting performance with AI-powered predictions for college basketball games.

## Overview

BetBoard helps users make informed sports betting decisions by providing predictions, odds comparison across sportsbooks, and comprehensive bet tracking with performance analytics.

## Features

### 🏀 Core Functionality
- **Predictions**: Machine learning-powered predictions with confidence ratings
- **Game Search**: Find games by team names and matchups
- **Bet Tracking**: Track your bets and monitor performance over time
- **Multiple Bet Types**: Support for Moneyline, Spread, and Total bets
- **Real-time Updates**: Live game results and bet outcome calculations

### 📈 Performance Analytics
- **Portfolio Performance**: Visual charts showing profit/loss over time
- **ROI Tracking**: Calculate and display return on investment
- **Bet History**: Complete history of all placed bets
- **Win/Loss Statistics**: Detailed breakdown of betting performance

### 🎯 User Experience
- **Clean Interface**: Modern SwiftUI design with intuitive navigation
- **Authentication**: Quick signup with Firebase auth
- **Customizable Settings**: Adjust odds format and notification preferences


## 📂 Directory Structure
### 1. functions/ (The Backend)
- This directory contains the Firebase Cloud Functions that run our daily automation logic.

- **automation/pipeline/:** The core "brains" of the system. Contains the prediction_pipeline (daily odds and projections) and evaluation_pipeline (grading past bets).

- **automation/processing/:** Logic for feature engineering and turning raw stats into model-ready data.

- **automation/clients/:** Dedicated wrappers for external APIs (The Odds API, KenPom/Torvik) and internal databases (Firestore).

- **main.py:** The entry point for cloud triggers and scheduled tasks.

### 2. iOS-BetBoard/ (The Frontend)
- A SwiftUI application following the MVVM architecture.

- **Model/:** Data structures for Games, Bets, and Users.

- **ViewModel/:** Business logic that bridges the UI and Firebase data.

- **View/:** Modular UI components, including the custom 3D Trophy view and interactive betting charts.

- **SportsAppTestTests/ & SportsAppTestUITests/:** Contains unit and integration tests for front end functionality.

### 3. data/ (The Vault)
- Storage for historical datasets and machine learning assets.

- **historical/:** CSV logs for game results and betting lines dating back to 2019.

- **xgb_model/ & lgb_model/:** Production-ready model artifacts, metadata, and feature importance mappings.

### 4. services/
- Utility scripts for manual data scraping and initial model training.

- **ml/:** Scripts used for training the XGBoost and LightGBM models.

- **scraper/:** Standalone scrapers for conference data and historical odds.

### 5. tests/
- The backend validation suite.

- Contains unit and integration tests for every step of the automation process, including data ingestion, feature math, and cloud function triggers.

## 🧪 Testing
- We use pytest to ensure the reliability of our data pipelines. Our test suite is designed to prevent "silent failures" in the data.

- We leverage the XCTest and XCUITest frameworks to perform automated unit and functional testing across the Swift-based frontend.

## 🛠 Tech Stack
- Backend: Python 3.11+, Firebase Functions, Firestore.

- ML: XGBoost, LightGBM, Pandas, Scikit-learn.

- Frontend: Swift, SwiftUI, Firebase Auth, Google Sign-In.

- Testing: Pytest, Coverage.py.




## Privacy & Disclaimer

⚠️ **Important Notice**: 
- This app is for educational and tracking purposes only
- No actual money or gambling transactions occur within the app
- Users are responsible for complying with local gambling laws
- Predictions are for informational purposes and not guaranteed outcomes



