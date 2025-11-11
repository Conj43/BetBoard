//
//  PredictionsViewModel.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//  Updated to handle moneyline bet types

import SwiftUI
import FirebaseAuth
import Firebase

// MARK: - PredictionsViewModel
@MainActor
class PredictionsViewModel: ObservableObject {
    @Published var predictions: [PredictionGame] = []
    @Published var filteredPredictions: [PredictionGame] = []
    @Published var isLoading: Bool = true
    @Published var errorMessage: String?
    
    // We're not using selectedBetType anymore as we're showing all predictions
    // But keeping it for compatibility with other views that might depend on it
    @Published var selectedBetType: BetType = .spread
    
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
            
            // Load prediction games from bet slips, but only include those with recommendations
            let predictionGames = await loadPredictionsWithRecommendations(from: activeBetSlips)
            print("🧠 Created \(predictionGames.count) prediction games with recommendations")
            
            // Sort predictions by odds_to_prob (high to low) instead of ranking
            let sortedPredictions = predictionGames.sorted { (game1, game2) -> Bool in
                let prob1 = game1.keyFactors.first(where: { $0.starts(with: "Win Probability:") })?
                    .dropFirst(16).dropLast(1).trimmingCharacters(in: .whitespaces) ?? "0"
                let prob2 = game2.keyFactors.first(where: { $0.starts(with: "Win Probability:") })?
                    .dropFirst(16).dropLast(1).trimmingCharacters(in: .whitespaces) ?? "0"
                
                return (Double(prob1) ?? 0) > (Double(prob2) ?? 0)
            }
            
            self.predictions = sortedPredictions
            // Instead of filtering, we just set filteredPredictions to all predictions
            self.filteredPredictions = sortedPredictions
            self.isLoading = false
            print("✅ Predictions loaded successfully: \(self.filteredPredictions.count) predictions")
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
    
    // MARK: - Load Predictions with Recommendations
    private func loadPredictionsWithRecommendations(from betSlips: [BetSlip]) async -> [PredictionGame] {
        print("🔄 Loading predictions with recommendations from \(betSlips.count) bet slips")
        
        var predictionGames: [PredictionGame] = []
        
        for betSlip in betSlips {
            // Fetch game data with recommended field from Firebase
            if let gameData = await fetchGameWithRecommendations(gameID: betSlip.gameID) {
                // Check if recommended exists and is an array
                if let recommendedArray = gameData["recommended"] as? [[String: Any]] {
                    print("✅ Found recommended data for game: \(betSlip.gameID) with \(recommendedArray.count) recommendations")
                    
                    // Process each recommendation in the array
                    for (index, recommendationData) in recommendedArray.enumerated() {
                        if let game = createPredictionGameFromRecommendation(
                            for: betSlip,
                            recommendationData: recommendationData,
                            ranking: index
                        ) {
                            predictionGames.append(game)
                            print("✅ Created prediction game with recommendation ranking: \(index)")
                        }
                    }
                } else {
                    // Try if it's a map with indices instead of an array
                    if let recommendedMap = gameData["recommended"] as? [String: [String: Any]] {
                        print("✅ Found recommended data (as map) for game: \(betSlip.gameID) with \(recommendedMap.count) recommendations")
                        
                        // Convert map to an array of (index, data) tuples and sort by index
                        let recommendations = recommendedMap.compactMap { key, value -> (Int, [String: Any])? in
                            if let index = Int(key) {
                                return (index, value)
                            }
                            return nil
                        }.sorted(by: { $0.0 < $1.0 })
                        
                        // Process each recommendation
                        for (index, recommendationData) in recommendations {
                            if let game = createPredictionGameFromRecommendation(
                                for: betSlip,
                                recommendationData: recommendationData,
                                ranking: index
                            ) {
                                predictionGames.append(game)
                                print("✅ Created prediction game with recommendation ranking: \(index)")
                            }
                        }
                    } else {
                        print("⚠️ No recommended field (or invalid format) for game: \(betSlip.gameID)")
                        print("⚠️ Available fields: \(gameData.keys.joined(separator: ", "))")
                        if let recValue = gameData["recommended"] {
                            print("⚠️ Recommended is of type: \(type(of: recValue))")
                        }
                    }
                }
            } else {
                print("⚠️ Could not fetch game data for: \(betSlip.gameID)")
            }
        }
        
        return predictionGames
    }
    
    // Fetch game data with recommendations from Firebase
    private func fetchGameWithRecommendations(gameID: String) async -> [String: Any]? {
        print("🔍 Fetching game data with recommendations for: \(gameID)")
        
        // Extract date from gameID
        let gameIDComponents = gameID.components(separatedBy: "_")
        guard gameIDComponents.count >= 2 else {
            print("❌ Invalid game ID format: \(gameID)")
            return nil
        }
        
        let dateStr = gameIDComponents[0]
        
        do {
            // Get the game document
            let gameDoc = try await Firestore.firestore().collection("games")
                                     .document(dateStr)
                                     .collection("games")
                                     .document(gameID)
                                     .getDocument()
            
            guard gameDoc.exists else {
                print("❌ Game document not found: \(gameID)")
                return nil
            }
            
            return gameDoc.data()
        } catch {
            print("❌ Error fetching game data: \(error.localizedDescription)")
            return nil
        }
    }
    
    // Create a prediction game from recommendation data
    private func createPredictionGameFromRecommendation(
        for betSlip: BetSlip,
        recommendationData: [String: Any],
        ranking: Int
    ) -> PredictionGame? {
        // Extract bet information from recommendation
        guard
            let betType = recommendationData["bet_type"] as? String,
            let bookLine = recommendationData["book_line"] as? Double,
            let bookmaker = recommendationData["bookmaker"] as? String,
            let edgeStrength = recommendationData["edge_strength"] as? Double,
            let selection = recommendationData["selection"] as? String
        else {
            print("❌ Missing required fields in recommendation data")
            print("⚠️ bet_type: \(recommendationData["bet_type"] ?? "missing")")
            print("⚠️ book_line: \(recommendationData["book_line"] ?? "missing")")
            print("⚠️ bookmaker: \(recommendationData["bookmaker"] ?? "missing")")
            print("⚠️ edge_strength: \(recommendationData["edge_strength"] ?? "missing")")
            print("⚠️ selection: \(recommendationData["selection"] ?? "missing")")
            return nil
        }
        
        // Optional fields
        let gameId = recommendationData["game_id"] as? String
        let modelProjection = recommendationData["model_projection"] as? Double
        let odds = recommendationData["odds"] as? Double ?? -110.0
        
        // Parse odds_to_prob which could be String or Double
        let oddsToProbDouble: Double
        if let probStr = recommendationData["odds_to_prob"] as? String {
            oddsToProbDouble = Double(probStr) ?? 0.0
        } else if let probDouble = recommendationData["odds_to_prob"] as? Double {
            oddsToProbDouble = probDouble
        } else {
            oddsToProbDouble = 0.0
        }
        
        // Map bet type to enum - ADD SUPPORT FOR MONEYLINE
        let betTypeEnum: BetType
        if betType.lowercased() == "total" {
            betTypeEnum = .total
        } else if betType.lowercased() == "moneyline" {
            betTypeEnum = .moneyline
        } else {
            betTypeEnum = .spread
        }
        
        // Map bookmaker to enum
        var sportsbookEnum: Sportsbook = .draftkings
        if let sbEnum = Sportsbook.allCases.first(where: { $0.rawValue.lowercased() == bookmaker.lowercased() }) {
            sportsbookEnum = sbEnum
        }
        
        // Create BestBet
        let bestBet = BestBet(
            type: betTypeEnum,
            selection: selection,
            odds: odds,
            sportsbook: sportsbookEnum
        )
        
        // Create key factors from recommendation data
        var keyFactors: [String] = [
            "Ranking: \(ranking)",
            "Book Line: \(bookLine)",
            "Edge Strength: \(String(format: "%.2f", edgeStrength))"
        ]
        
        if let modelProj = modelProjection {
            keyFactors.append("Model Projection: \(String(format: "%.2f", modelProj))")
        }
        
        if oddsToProbDouble > 0 {
            let percentage = oddsToProbDouble * 100
            keyFactors.append("Win Probability: \(String(format: "%.1f", percentage))%")
        }
        
        // Calculate confidence based on edge strength
        let confidence = min(max(50 + edgeStrength * 5, 50), 95) // Scale to 50-95 range
        
        // Create the prediction game
        let predictionGame = PredictionGame(
            homeTeam: betSlip.homeTeam,
            awayTeam: betSlip.awayTeam,
            gameTime: betSlip.gameTime,
            bestBet: bestBet,
            confidence: confidence,
            analysis: "Edge strength: \(String(format: "%.1f", edgeStrength * 100))pts, Win probability: \(String(format: "%.1f", oddsToProbDouble * 100))%",
            keyFactors: keyFactors,
            betSlip: betSlip
        )
        
        return predictionGame
    }
    
    // Keep filterPredictions for backwards compatibility but make it a no-op
    func filterPredictions(by betType: BetType) {
        // We're no longer filtering by bet type, just maintaining all predictions
        self.selectedBetType = betType
        self.filteredPredictions = self.predictions
        print("📊 Showing all \(self.filteredPredictions.count) predictions (no filtering)")
    }
    
    // MARK: - Refresh
    func refreshPredictions() async {
        print("🔄 Refreshing predictions...")
        self.isLoading = true
        self.errorMessage = nil
        await loadPredictions()
    }
    
    // MARK: - Bet Tracking Functions
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
