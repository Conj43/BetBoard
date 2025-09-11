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
            let betSlips = try await firebaseService.fetchBetSlips()
            let predictionGames = convertBetSlipsToPredictions(betSlips)
            
            await MainActor.run {
                self.predictions = predictionGames
                self.filterPredictions(by: self.selectedBetType)
                self.isLoading = false
            }
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to load predictions: \(error.localizedDescription)"
                self.isLoading = false
            }
        }
    }
    
    private func convertBetSlipsToPredictions(_ betSlips: [BetSlip]) -> [PredictionGame] {
        return betSlips.compactMap { betSlip in
            guard let predictionInfo = betSlip.predictionInfo,
                  let recommendedBet = predictionInfo.recommendedBet else {
                return nil
            }
            
            // Determine bet type from recommended bet
            let betType: BetType
            if recommendedBet.contains("ML") {
                betType = .moneyline
            } else if recommendedBet.contains("Over") || recommendedBet.contains("Under") {
                betType = .total
            } else {
                betType = .spread
            }
            
            // Find corresponding odds
            let odds: Double
            switch betType {
            case .moneyline:
                let teamName = recommendedBet.replacingOccurrences(of: " ML", with: "")
                odds = betSlip.bettingLines.moneyline[teamName] ?? -110
            case .spread:
                odds = betSlip.bettingLines.spread[recommendedBet] ?? -110
            case .total:
                odds = betSlip.bettingLines.total[recommendedBet] ?? -110
            }
            
            let bestBet = BestBet(
                type: betType,
                selection: recommendedBet,
                odds: odds,
                sportsbook: betSlip.sportsbook
            )
            
            let keyFactors = generateKeyFactors(for: betSlip, betType: betType)
            
            return PredictionGame(
                homeTeam: betSlip.homeTeam,
                awayTeam: betSlip.awayTeam,
                gameTime: betSlip.gameTime,
                bestBet: bestBet,
                confidence: predictionInfo.confidence,
                analysis: predictionInfo.analysis,
                keyFactors: keyFactors,
                betSlip: betSlip
            )
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
        filteredPredictions = predictions.filter { prediction in
            prediction.bestBet.type == betType
        }.sorted { $0.confidence > $1.confidence }
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
