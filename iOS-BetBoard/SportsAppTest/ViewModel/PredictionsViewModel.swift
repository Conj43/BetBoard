//
//  PredictionsViewModel.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI
import FirebaseAuth
import Firebase

// MARK: - PredictionsViewModel
@MainActor
class PredictionsViewModel: ObservableObject {
    @Published var predictions: [PredictionGame] = []
    @Published var filteredPredictions: [PredictionGame] = []
    @Published var selectedBetType: BetType = .spread
    @Published var isLoading: Bool = true
    @Published var errorMessage: String?
    
    private var gameStatusCache: [String: GameStatus] = [:]
    private let firebaseService = FirebaseService()
    
    func loadPredictions() async {
        print("🔄 Loading predictions...")
        
        do {
            // First, load all bet slips
            let betSlips = try await firebaseService.fetchBetSlips()
            print("📊 Fetched \(betSlips.count) bet slips")
            
            // Fetch game statuses for filtering
            await loadGameStatuses(for: betSlips.map { $0.gameID })
            
            // Filter active games (not yet played or in progress)
            let activeBetSlips = betSlips.filter { betSlip in
                guard let gameStatus = self.gameStatusCache[betSlip.gameID] else {
                    print("⚠️ No game status found for betSlip gameID: \(betSlip.gameID), including it anyway")
                    return true
                }
                
                // Only include games that are not final
                switch gameStatus {
                case .final:
                    print("❌ Excluding final game: \(betSlip.gameID)")
                    return false
                case .notPlayed, .inProgress:
                    print("✅ Including active game: \(betSlip.gameID)")
                    return true
                }
            }
            
            print("🎯 Active bet slips after filtering: \(activeBetSlips.count)")
            
            let predictionGames = convertBetSlipsToPredictions(activeBetSlips)
            print("🧠 Created \(predictionGames.count) prediction games")
            
            self.predictions = predictionGames
            self.filterPredictions(by: self.selectedBetType)
            self.isLoading = false
            print("✅ Predictions loaded successfully: \(self.filteredPredictions.count) filtered predictions")
        } catch {
            self.errorMessage = "Failed to load predictions: \(error.localizedDescription)"
            self.isLoading = false
            print("❌ Error loading predictions: \(error)")
        }
    }
    
    private func loadGameStatuses(for gameIDs: [String]) async {
        print("🔄 Loading game statuses for \(gameIDs.count) games...")
        
        // In a real implementation, this would fetch game statuses from a service
        // For now, we'll just simulate by marking all as not played
        for gameID in gameIDs {
            gameStatusCache[gameID] = .notPlayed
        }
        
        print("✅ Loaded game statuses")
    }
    
    private func convertBetSlipsToPredictions(_ betSlips: [BetSlip]) -> [PredictionGame] {
        print("🔄 Converting \(betSlips.count) bet slips to predictions...")
        
        var predictionGames: [PredictionGame] = []
        
        for betSlip in betSlips {
            print("🎯 Processing bet slip: \(betSlip.id) - \(betSlip.homeTeam.shortName) vs \(betSlip.awayTeam.shortName)")
            
            guard let predictionInfo = betSlip.predictionInfo else {
                print("⚠️ No prediction info for bet slip: \(betSlip.id)")
                continue
            }
            
            // Create predictions for each bet type if available
            let games = createPredictionGames(for: betSlip, with: predictionInfo)
            predictionGames.append(contentsOf: games)
        }
        
        return predictionGames
    }
    
    private func createPredictionGames(for betSlip: BetSlip, with predictionInfo: PredictionInfo) -> [PredictionGame] {
        var games: [PredictionGame] = []
        
        // Process moneyline bet if available
        if let moneylineBet = predictionInfo.moneylineBet, predictionInfo.moneylineConfidence > 0 {
            print("🔍 Processing moneyline prediction: \(moneylineBet) with \(predictionInfo.moneylineConfidence)% confidence")
            
            if let game = createPredictionGame(
                for: betSlip,
                betType: .moneyline,
                selection: moneylineBet,
                confidence: predictionInfo.moneylineConfidence
            ) {
                games.append(game)
                print("✅ Created moneyline prediction game")
            }
        }
        
        // Process spread bet if available
        if let spreadBet = predictionInfo.spreadBet, predictionInfo.spreadConfidence > 0 {
            print("🔍 Processing spread prediction: \(spreadBet) with \(predictionInfo.spreadConfidence)% confidence")
            
            if let game = createPredictionGame(
                for: betSlip,
                betType: .spread,
                selection: spreadBet,
                confidence: predictionInfo.spreadConfidence
            ) {
                games.append(game)
                print("✅ Created spread prediction game")
            }
        }
        
        // Process total bet if available
        if let totalBet = predictionInfo.totalBet, predictionInfo.totalConfidence > 0 {
            print("🔍 Processing total prediction: \(totalBet) with \(predictionInfo.totalConfidence)% confidence")
            
            if let game = createPredictionGame(
                for: betSlip,
                betType: .total,
                selection: totalBet,
                confidence: predictionInfo.totalConfidence
            ) {
                games.append(game)
                print("✅ Created total prediction game")
            }
        }
        
        // If no predictions were created but we have the old-style recommendedBet,
        // fall back to using that for backward compatibility
        if games.isEmpty, let recommendedBet = predictionInfo.recommendedBet, predictionInfo.confidence > 0 {
            print("🔍 Falling back to legacy prediction: \(recommendedBet) with \(predictionInfo.confidence)% confidence")
            
            // Determine bet type from recommended bet
            let betType = determineBetType(from: recommendedBet)
            
            if let game = createPredictionGame(
                for: betSlip,
                betType: betType,
                selection: recommendedBet,
                confidence: predictionInfo.confidence
            ) {
                games.append(game)
                print("✅ Created legacy prediction game")
            }
        }
        
        return games
    }
    
    private func determineBetType(from betString: String) -> BetType {
        if betString.contains("ML") || betString.contains("MONEY") {
            return .moneyline
        } else if betString.contains("OVER") || betString.contains("UNDER") || betString.contains("Over") || betString.contains("Under") {
            return .total
        } else {
            return .spread
        }
    }
    
    private func createPredictionGame(
        for betSlip: BetSlip,
        betType: BetType,
        selection: String,
        confidence: Double
    ) -> PredictionGame? {
        print("🏀 Creating prediction game for: \(betSlip.homeTeam.shortName) vs \(betSlip.awayTeam.shortName), bet: \(selection)")
        
        // Find corresponding odds
        let odds: Double
        
        switch betType {
        case .moneyline:
            // Extract team name from selection (which might be just the team name or include "ML")
            let teamName: String
            if selection.contains("ML") {
                teamName = selection.replacingOccurrences(of: " ML", with: "")
            } else {
                teamName = selection
            }
            
            if let foundOdds = betSlip.bettingLines.moneyline[teamName.uppercased()] {
                odds = foundOdds
            } else {
                print("⚠️ Could not find moneyline odds for \(teamName) - available keys: \(betSlip.bettingLines.moneyline.keys)")
                odds = -110 // Default odds
            }
            
        case .spread:
            if let foundOdds = betSlip.bettingLines.spread[selection] {
                odds = foundOdds
            } else {
                print("⚠️ Could not find spread odds for \(selection) - available keys: \(betSlip.bettingLines.spread.keys)")
                odds = -110 // Default odds
            }
            
        case .total:
            if let foundOdds = betSlip.bettingLines.total[selection] {
                odds = foundOdds
            } else {
                print("⚠️ Could not find total odds for \(selection) - available keys: \(betSlip.bettingLines.total.keys)")
                odds = -110 // Default odds
            }
        }
        
        let bestBet = BestBet(
            type: betType,
            selection: selection,
            odds: odds,
            sportsbook: betSlip.sportsbook
        )
        
        let keyFactors = generateKeyFactors(for: betSlip, betType: betType)
        
        let predictionGame = PredictionGame(
            homeTeam: betSlip.homeTeam,
            awayTeam: betSlip.awayTeam,
            gameTime: betSlip.gameTime,
            bestBet: bestBet,
            confidence: confidence,
            analysis: betSlip.predictionInfo?.analysis,
            keyFactors: keyFactors,
            betSlip: betSlip
        )
        
        return predictionGame
    }
    
    private func generateKeyFactors(for betSlip: BetSlip, betType: BetType) -> [String] {
        var factors: [String] = []
        
        // Add team-specific factors
        if let homeRanking = betSlip.homeTeam.ranking {
            factors.append("Home team ranked #\(homeRanking)")
        }
        
        if let awayRanking = betSlip.awayTeam.ranking {
            factors.append("Away team ranked #\(awayRanking)")
        }
        
        // Add conference info
        if betSlip.homeTeam.conference == betSlip.awayTeam.conference {
            factors.append("Conference matchup (\(betSlip.homeTeam.conference))")
        }
        
        // Add neutral site factor
        if betSlip.neutralSite {
            factors.append("Neutral site game")
        }
        
        // Add bet-specific factors based on type
        switch betType {
        case .spread:
            factors.append("Strong defensive matchup")
            factors.append("Home court advantage considerations")
        case .moneyline:
            factors.append("Recent head-to-head record")
            factors.append("Current team momentum")
        case .total:
            factors.append("Teams' pace of play analysis")
            factors.append("Weather/venue conditions")
        }
        
        return factors
    }
    
    func filterPredictions(by betType: BetType) {
        print("🔍 Filtering \(predictions.count) predictions by bet type: \(betType.rawValue)")
        
        // First, filter all predictions to only include those matching the selected bet type
        filteredPredictions = predictions.filter { prediction in
            return prediction.bestBet.type == betType
        }
        
        // The filteredPredictions now only contain games with the selected bet type
        // Since each PredictionGame already has the appropriate confidence value for its bet type,
        // we can just sort by the confidence property
        filteredPredictions = filteredPredictions.sorted { first, second in
            return first.confidence > second.confidence
        }
        
        print("✅ Filtered to \(filteredPredictions.count) predictions for \(betType.rawValue)")
    }
    
    func refreshPredictions() async {
        await loadPredictions()
    }
    
    func trackSpecificBet(from prediction: PredictionGame, betType: BetType, selection: String, odds: Double, amount: Double) async {
        guard let currentUser = Auth.auth().currentUser else {
            errorMessage = "Please log in to track bets"
            return
        }
        
        let bet = Bet(
            id: UUID().uuidString,
            userID: currentUser.uid,
            gameID: prediction.betSlip.gameID,
            type: betType,
            selection: selection,
            odds: odds,
            amount: amount,
            result: .pending,
            placedAt: Date()
        )
        
        do {
            try await firebaseService.addUserBet(bet)
            // Clear any previous errors
            errorMessage = nil
        } catch {
            errorMessage = "Failed to track bet: \(error.localizedDescription)"
        }
    }
    
    // Keep the old method for backwards compatibility, but now it defaults to $0 amount
    func trackBet(from prediction: PredictionGame) async {
        await trackSpecificBet(
            from: prediction,
            betType: prediction.bestBet.type,
            selection: prediction.bestBet.selection,
            odds: prediction.bestBet.odds,
            amount: 0.0
        )
    }
}
