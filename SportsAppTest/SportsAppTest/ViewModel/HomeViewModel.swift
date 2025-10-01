//
//  HomeViewModel.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation
import Combine
import FirebaseAuth

@MainActor
class HomeViewModel: ObservableObject {
    @Published var trackedBets: [BetWithGameInfo] = []
    @Published var recentBets: [BetWithGameInfo] = []
    @Published var chartData: [ChartDataPoint] = []
    @Published var totalPnL: Double = 0.0
    @Published var roi: Double = 0.0
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private let firebaseService = FirebaseService()
    private var cancellables = Set<AnyCancellable>()
    private var gameCache: [String: Game] = [:]
    
    var totalPnLFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencySymbol = "$"
        formatter.maximumFractionDigits = 0
        let sign = totalPnL >= 0 ? "+" : ""
        return sign + (formatter.string(from: NSNumber(value: totalPnL)) ?? "$0")
    }
    
    var roiFormatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .percent
        formatter.maximumFractionDigits = 1
        let sign = roi >= 0 ? "+" : ""
        return sign + (formatter.string(from: NSNumber(value: roi / 100)) ?? "0%")
    }
    
    func loadData() {
        guard let currentUser = Auth.auth().currentUser else {
            errorMessage = "Please log in to view your data"
            return
        }
        
        isLoading = true
        errorMessage = nil
        
        Task {
            do {
                // Load games first to build cache
                let games = try await firebaseService.fetchGames()
                await MainActor.run {
                    for game in games {
                        self.gameCache[game.id] = game
                    }
                }
                
                let userBets = try await firebaseService.fetchUserBets(for: currentUser.uid)
                
                await MainActor.run {
                    self.processUserBets(userBets)
                    self.calculateMetrics(from: userBets)
                    self.updateChartData(for: .oneWeek, from: userBets)
                    self.isLoading = false
                }
            } catch {
                await MainActor.run {
                    self.errorMessage = "Failed to load data: \(error.localizedDescription)"
                    self.isLoading = false
                }
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
                self.trackedBets.removeAll { $0.id == betWithGameInfo.id }
                self.recentBets.removeAll { $0.id == betWithGameInfo.id }
                
                // Recalculate metrics with remaining bets
                let remainingBets = self.getAllUniqueBets()
                self.calculateMetrics(from: remainingBets)
                self.updateChartData(for: .oneWeek, from: remainingBets)
            }
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to delete bet: \(error.localizedDescription)"
            }
        }
    }
    
    private func processUserBets(_ bets: [Bet]) {
        let sortedBets = bets.sorted { $0.placedAt > $1.placedAt }
        
        // Convert bets to BetWithGameInfo
        let trackedBetsWithInfo = sortedBets.filter { $0.result == .pending }.compactMap { bet in
            createBetWithGameInfo(from: bet)
        }
        
        let recentBetsWithInfo = Array(sortedBets.prefix(10)).compactMap { bet in
            createBetWithGameInfo(from: bet)
        }
        
        trackedBets = trackedBetsWithInfo
        recentBets = recentBetsWithInfo
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
    
    private func calculateMetrics(from bets: [Bet]) {
        let settledBets = bets.filter { $0.result != .pending }
        let totalWagered = settledBets.reduce(0) { $0 + $1.amount }
        
        var totalProfit: Double = 0 // Changed from totalPayout to totalProfit for clarity
        
        for bet in settledBets {
            let profit = calculateBetProfit(bet: bet)
            totalProfit += profit
        }
        
        totalPnL = totalProfit
        roi = totalWagered > 0 ? (totalPnL / totalWagered) * 100 : 0
        
        print("📊 Metrics calculated - Total Wagered: $\(totalWagered), Total P&L: $\(totalPnL), ROI: \(roi)%")
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
            return winnings // Return just the profit, not including the original bet amount
        case .lost:
            return -bet.amount // Lost the entire bet amount
        case .push:
            return 0 // No gain, no loss
        case .pending:
            return 0 // Don't count pending bets
        }
    }
    
    func updateChartData(for timeframe: TimeFrame, from allBets: [Bet]? = nil) {
        let calendar = Calendar.current
        let now = Date()
        
        let startDate: Date
        switch timeframe {
        case .oneDay:
            startDate = calendar.date(byAdding: .day, value: -1, to: now) ?? now
        case .oneWeek:
            startDate = calendar.date(byAdding: .weekOfYear, value: -1, to: now) ?? now
        case .oneMonth:
            startDate = calendar.date(byAdding: .month, value: -1, to: now) ?? now
        case .threeMonths:
            startDate = calendar.date(byAdding: .month, value: -3, to: now) ?? now
        case .ytd:
            startDate = calendar.date(from: DateComponents(year: calendar.component(.year, from: now), month: 1, day: 1)) ?? now
        case .allTime:
            startDate = allBets?.min(by: { $0.placedAt < $1.placedAt })?.placedAt ?? now
        }
        
        let betsToUse = allBets ?? getAllUniqueBets()
        let filteredBets = betsToUse.filter { $0.placedAt >= startDate && $0.result != .pending }
            .sorted { $0.placedAt < $1.placedAt }
        
        var runningPnL: Double = 0
        var dataPoints: [ChartDataPoint] = []
        
        // Add starting point
        dataPoints.append(ChartDataPoint(date: startDate, pnl: 0))
        
        for bet in filteredBets {
            let betProfit = calculateBetProfit(bet: bet)
            runningPnL += betProfit
            dataPoints.append(ChartDataPoint(date: bet.placedAt, pnl: runningPnL))
            
            print("📈 Chart data point: \(bet.selection) - Profit: $\(betProfit), Running P&L: $\(runningPnL)")
        }
        
        // Add current point if needed
        if let lastPoint = dataPoints.last, lastPoint.date < now {
            dataPoints.append(ChartDataPoint(date: now, pnl: runningPnL))
        }
        
        // If no data, show a flat line at 0
        if dataPoints.count <= 1 {
            dataPoints = [
                ChartDataPoint(date: startDate, pnl: 0),
                ChartDataPoint(date: now, pnl: 0)
            ]
        }
        
        chartData = dataPoints
        print("📊 Final chart data points: \(dataPoints.count)")
    }
    
    // Helper function to get all unique bets from both tracked and recent
    private func getAllUniqueBets() -> [Bet] {
        var allBets: [Bet] = []
        var seenBetIDs = Set<String>()
        
        for betInfo in trackedBets {
            if !seenBetIDs.contains(betInfo.bet.id) {
                allBets.append(betInfo.bet)
                seenBetIDs.insert(betInfo.bet.id)
            }
        }
        
        for betInfo in recentBets {
            if !seenBetIDs.contains(betInfo.bet.id) {
                allBets.append(betInfo.bet)
                seenBetIDs.insert(betInfo.bet.id)
            }
        }
        
        return allBets
    }
    
    func refreshData() {
        loadData()
    }
}
