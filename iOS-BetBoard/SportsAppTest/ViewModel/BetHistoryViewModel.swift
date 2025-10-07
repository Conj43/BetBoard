//
//  BetHistoryViewModel.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


//
//  BetHistoryViewModel.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation
import Combine
import FirebaseAuth

@MainActor
class BetHistoryViewModel: ObservableObject {
    @Published var allBets: [BetWithGameInfo] = []
    @Published var filteredBets: [BetWithGameInfo] = []
    @Published var totalBets: Int = 0
    @Published var winRate: Double = 0.0
    @Published var totalPnL: Double = 0.0
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private let firebaseService = FirebaseService()
    private var gameCache: [String: Game] = [:]
    
    // Computed properties for formatting
    var winRateFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .percent
        formatter.maximumFractionDigits = 1
        return formatter.string(from: NSNumber(value: winRate / 100)) ?? "0%"
    }
    
    var totalPnLFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencySymbol = "$"
        formatter.maximumFractionDigits = 0
        let sign = totalPnL >= 0 ? "+" : ""
        return sign + (formatter.string(from: NSNumber(value: totalPnL)) ?? "$0")
    }
    
    func loadBetHistory() async {
        guard let currentUser = Auth.auth().currentUser else {
            errorMessage = "Please log in to view your bet history"
            return
        }
        
        isLoading = true
        errorMessage = nil
        
        do {
            // Load games first to build cache
            let games = try await firebaseService.fetchGames()
            await MainActor.run {
                for game in games {
                    self.gameCache[game.id] = game
                }
            }
            
            // Load user bets
            let userBets = try await firebaseService.fetchUserBets(for: currentUser.uid)
            
            await MainActor.run {
                self.processUserBets(userBets)
                self.calculateStats()
                self.applyFilters(filter: .all, sort: .dateNewest) // Default filter and sort
                self.isLoading = false
            }
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to load bet history: \(error.localizedDescription)"
                self.isLoading = false
            }
        }
    }
    
    func deleteBet(_ betWithGameInfo: BetWithGameInfo) async {
        guard let currentUser = Auth.auth().currentUser else {
            errorMessage = "Please log in to delete bets"
            return
        }
        
        do {
            try await firebaseService.deleteUserBet(betID: betWithGameInfo.bet.id, userID: currentUser.uid)
            
            // Remove the bet from local arrays
            await MainActor.run {
                self.allBets.removeAll { $0.id == betWithGameInfo.id }
                self.filteredBets.removeAll { $0.id == betWithGameInfo.id }
                
                // Recalculate stats
                self.calculateStats()
            }
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to delete bet: \(error.localizedDescription)"
            }
        }
    }
    
    func applyFilters(filter: BetResultFilter, sort: SortOption) {
        var filtered = allBets
        
        // Apply result filter
        switch filter {
        case .all:
            break // Show all bets
        case .won:
            filtered = filtered.filter { $0.bet.result == .won }
        case .lost:
            filtered = filtered.filter { $0.bet.result == .lost }
        case .pending:
            filtered = filtered.filter { $0.bet.result == .pending }
        case .push:
            filtered = filtered.filter { $0.bet.result == .push }
        }
        
        // Apply sort
        switch sort {
        case .dateNewest:
            filtered = filtered.sorted { $0.bet.placedAt > $1.bet.placedAt }
        case .dateOldest:
            filtered = filtered.sorted { $0.bet.placedAt < $1.bet.placedAt }
        case .amountHighest:
            filtered = filtered.sorted { $0.bet.amount > $1.bet.amount }
        case .amountLowest:
            filtered = filtered.sorted { $0.bet.amount < $1.bet.amount }
        }
        
        filteredBets = filtered
    }
    
    private func processUserBets(_ bets: [Bet]) {
        let betsWithInfo = bets.compactMap { bet in
            createBetWithGameInfo(from: bet)
        }
        
        allBets = betsWithInfo
    }
    
    private func createBetWithGameInfo(from bet: Bet) -> BetWithGameInfo? {
        guard let game = gameCache[bet.gameID] else {
            print("⚠️ Could not find game info for bet: \(bet.id)")
            // Return a fallback with game ID
            return BetWithGameInfo(
                bet: bet,
                homeTeam: "Unknown",
                awayTeam: "Unknown",
                gameDate: bet.placedAt
            )
        }
        
        return BetWithGameInfo(
            bet: bet,
            homeTeam: game.homeTeam,
            awayTeam: game.awayTeam,
            gameDate: game.date
        )
    }
    
    private func calculateStats() {
        let settledBets = allBets.filter { $0.bet.result != .pending }
        let wonBets = settledBets.filter { $0.bet.result == .won }
        
        totalBets = allBets.count
        winRate = settledBets.isEmpty ? 0.0 : (Double(wonBets.count) / Double(settledBets.count)) * 100
        
        // Calculate total P&L
        var totalProfit: Double = 0
        
        for betInfo in settledBets {
            let profit = calculateBetProfit(bet: betInfo.bet)
            totalProfit += profit
        }
        
        totalPnL = totalProfit
        
        print("📊 Bet History Stats - Total: \(totalBets), Win Rate: \(winRate)%, Total P&L: $\(totalPnL)")
    }
    
    // Helper function to calculate profit/loss for a single bet
    private func calculateBetProfit(bet: Bet) -> Double {
        switch bet.result {
        case .won:
            // Calculate winnings based on odds
            let winnings: Double
            if bet.odds > 0 {
                // Positive odds: bet $100 to win $odds
                winnings = bet.amount * (bet.odds / 100)
            } else {
                // Negative odds: bet $odds to win $100
                winnings = bet.amount * (100 / abs(bet.odds))
            }
            return winnings // Return just the profit
        case .lost:
            return -bet.amount // Lost the entire bet amount
        case .push:
            return 0 // No gain, no loss
        case .pending:
            return 0 // Don't count pending bets
        }
    }
}