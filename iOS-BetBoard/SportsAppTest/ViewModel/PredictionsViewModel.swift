//
//  PredictionsViewModel.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation
import Combine
import FirebaseAuth

@MainActor
class PredictionsViewModel: ObservableObject {
    @Published var predictions: [PredictionGame] = []
    @Published var filteredPredictions: [PredictionGame] = []
    @Published var selectedBetType: BetType = .spread
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private let firebaseService = FirebaseService()
    private var cancellables = Set<AnyCancellable>()
    private var gameStatusCache: [String: GameStatus] = [:] // Cache for game statuses
    
    init() {
        // Listen for bet type changes
        $selectedBetType
            .sink { [weak self] betType in
                self?.filterPredictions(by: betType)
            }
            .store(in: &cancellables)
    }
    
    func loadPredictions() async {
        isLoading = true
        errorMessage = nil
        
        do {
            print("🔍 Starting to load predictions...")
            
            // Load both bet slips and games to get game statuses
            async let betSlipsTask = firebaseService.fetchBetSlips()
            async let gamesTask = firebaseService.fetchGames()
            
            let (betSlips, games) = try await (betSlipsTask, gamesTask)
            
            print("📊 Loaded \(betSlips.count) bet slips and \(games.count) games")
            
            // Build game status cache
            await MainActor.run {
                for game in games {
                    self.gameStatusCache[game.id] = game.status
                    print("🎮 Game \(game.id): \(game.homeTeam) vs \(game.awayTeam) - Status: \(game.status)")
                }
            }
            
            // Filter out bet slips for games that are already final
            let activeBetSlips = betSlips.filter { betSlip in
                guard let gameStatus = gameStatusCache[betSlip.gameID] else {
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
            
            await MainActor.run {
                self.predictions = predictionGames
                self.filterPredictions(by: self.selectedBetType)
                self.isLoading = false
                print("✅ Predictions loaded successfully: \(self.filteredPredictions.count) filtered predictions")
            }
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to load predictions: \(error.localizedDescription)"
                self.isLoading = false
                print("❌ Error loading predictions: \(error)")
            }
        }
    }
    
    private func convertBetSlipsToPredictions(_ betSlips: [BetSlip]) -> [PredictionGame] {
        print("🔄 Converting \(betSlips.count) bet slips to predictions...")
        
        return betSlips.compactMap { betSlip in
            print("🎯 Processing bet slip: \(betSlip.id) - \(betSlip.homeTeam.shortName) vs \(betSlip.awayTeam.shortName)")
            
            guard let predictionInfo = betSlip.predictionInfo,
                  let recommendedBet = predictionInfo.recommendedBet else {
                print("⚠️ No prediction info for bet slip: \(betSlip.id)")
                return nil
            }
            
            print("🧠 Found prediction info: \(recommendedBet) with \(predictionInfo.confidence)% confidence")
            
            // Determine bet type from recommended bet
            let betType: BetType
            if recommendedBet.contains("ML") {
                betType = .moneyline
            } else if recommendedBet.contains("Over") || recommendedBet.contains("Under") {
                betType = .total
            } else {
                betType = .spread
            }
            
            print("📈 Determined bet type: \(betType.rawValue)")
            
            // Find corresponding odds
            let odds: Double
            switch betType {
            case .moneyline:
                let teamName = recommendedBet.replacingOccurrences(of: " ML", with: "")
                odds = betSlip.bettingLines.moneyline[teamName] ?? -110
                print("💰 Moneyline odds for \(teamName): \(odds)")
            case .spread:
                odds = betSlip.bettingLines.spread[recommendedBet] ?? -110
                print("📊 Spread odds for \(recommendedBet): \(odds)")
            case .total:
                odds = betSlip.bettingLines.total[recommendedBet] ?? -110
                print("🎯 Total odds for \(recommendedBet): \(odds)")
            }
            
            let bestBet = BestBet(
                type: betType,
                selection: recommendedBet,
                odds: odds,
                sportsbook: betSlip.sportsbook
            )
            
            let keyFactors = generateKeyFactors(for: betSlip, betType: betType)
            
            let predictionGame = PredictionGame(
                homeTeam: betSlip.homeTeam,
                awayTeam: betSlip.awayTeam,
                gameTime: betSlip.gameTime,
                bestBet: bestBet,
                confidence: predictionInfo.confidence,
                analysis: predictionInfo.analysis,
                keyFactors: keyFactors,
                betSlip: betSlip
            )
            
            print("✅ Created prediction game: \(predictionGame.homeTeam.shortName) vs \(predictionGame.awayTeam.shortName)")
            return predictionGame
        }
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
    
    private func filterPredictions(by betType: BetType) {
        print("🔍 Filtering \(predictions.count) predictions by bet type: \(betType.rawValue)")
        
        filteredPredictions = predictions.filter { prediction in
            prediction.bestBet.type == betType
        }.sorted { $0.confidence > $1.confidence }
        
        print("✅ Filtered to \(filteredPredictions.count) predictions")
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
