# BetBoard 📊

A SwiftUI-based iOS application for tracking sports betting performance with AI-powered predictions for college basketball games.

## Overview

BetBoard helps users make informed sports betting decisions by providing AI predictions, odds comparison across sportsbooks, and comprehensive bet tracking with performance analytics.

## Features

### 🏀 Core Functionality
- **AI Predictions**: Machine learning-powered predictions with confidence ratings
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
- **Dark Mode Support**: Toggle between light and dark themes
- **Anonymous Authentication**: Quick signup with Firebase anonymous auth
- **Customizable Settings**: Adjust odds format and notification preferences

## Tech Stack

- **Frontend**: SwiftUI
- **Backend**: Firebase (Firestore, Authentication)
- **Charts**: Swift Charts framework
- **Architecture**: MVVM pattern with ObservableObject ViewModels

## Project Structure

```
SportsAppTest/
├── Views/
│   ├── ContentView.swift           # Main app container
│   ├── AuthView.swift             # Authentication screen
│   ├── HomeView.swift             # Dashboard with performance metrics
│   ├── SearchView.swift           # Game search functionality
│   ├── PredictionsView.swift      # AI predictions display
│   ├── AdminView.swift            # Game result management
│   └── InfoView.swift             # Settings and app info
├── ViewModels/
│   ├── HomeViewModel.swift        # Home screen logic
│   ├── SearchViewModel.swift      # Search functionality
│   ├── PredictionsViewModel.swift # Predictions management
│   └── InfoViewModel.swift        # Settings management
├── Models/
│   ├── Bet.swift                  # Bet data structure
│   ├── Game.swift                 # Game information
│   ├── Team.swift                 # Team details
│   ├── BetSlip.swift             # Betting slip with odds
│   └── Enums.swift               # App enumerations
├── Services/
│   ├── AuthService.swift         # Authentication logic
│   ├── FirebaseService.swift     # Database operations
│   └── GameResultUpdater.swift   # Game result management
└── UI Components/
    ├── BetSlipUI.swift           # Interactive betting interface
    ├── TrackedBetSlipView.swift  # Bet details display
    └── ChartView.swift           # Performance charts
```

## Installation

### Prerequisites
- Xcode 15.0+
- iOS 16.0+
- CocoaPods or Swift Package Manager
- Firebase project setup

### Setup

1. **Clone the repository**
```bash
git clone [your-repo-url]
cd BetBoard
```

2. **Firebase Setup**
   - Create a new Firebase project at [https://console.firebase.google.com](https://console.firebase.google.com)
   - Enable Authentication (Anonymous sign-in)
   - Create a Firestore database
   - Download `GoogleService-Info.plist` and add to your Xcode project

3. **Install Dependencies**
   The project uses Firebase SDK via Swift Package Manager. Dependencies should be automatically resolved when opening the project in Xcode.

4. **Configure Firestore Security Rules**
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
      
      match /bets/{betId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
    }
    
    // Public game data
    match /games/{gameId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null; // Adjust based on admin requirements
    }
    
    // Public betting lines
    match /bettingLines/{lineId} {
      allow read: if request.auth != null;
    }
  }
}
```

## Key Components

### Authentication
- Anonymous Firebase authentication for quick user onboarding
- Automatic user profile creation
- Secure user data isolation

### Bet Tracking System
- **Bet Types**: Moneyline, Spread, Total (Over/Under)
- **Results Calculation**: Automatic bet outcome determination
- **Performance Metrics**: ROI, win rate, profit/loss tracking

### AI Predictions
- Confidence-based predictions (0-100%)
- Key factors analysis
- Recommended bet suggestions
- Multiple sportsbook odds comparison

### Admin Features
- Game result management
- Bet outcome calculation testing
- Debug tools for bet logic verification

## Data Models

### Core Models
- **Bet**: Individual bet with type, selection, odds, amount
- **Game**: Game information with teams, date, status
- **Team**: Team details with record, ranking, conference
- **BetSlip**: Complete betting interface with odds and predictions

### Enums
- **BetType**: moneyline, spread, total
- **BetResult**: won, lost, push, pending
- **GameStatus**: notPlayed, inProgress, final

## Configuration

The app includes several customizable settings:
- Odds format (American, Decimal, Fractional)
- Push notifications
- Dark mode toggle
- Performance tracking preferences

## Testing

### Debug Features
- **Admin Panel**: Manually set game results for testing
- **Bet Calculator**: Debug tool for verifying bet calculations
- **Mock Data**: Sample data for development and testing

### Testing Bet Logic
The app includes comprehensive bet result calculation:
- Moneyline: Winner determination
- Spread: Point spread coverage calculation
- Total: Over/under game total comparison

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Privacy & Disclaimer

⚠️ **Important Notice**: 
- This app is for educational and tracking purposes only
- No actual money or gambling transactions occur within the app
- Users are responsible for complying with local gambling laws
- AI predictions are for informational purposes and not guaranteed outcomes

## License


## Acknowledgments

- Firebase for backend services
- SwiftUI for the modern iOS interface
- Swift Charts for performance visualization
- College basketball data providers - TBD

## Contact
