//
//  HomeView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI
import Charts

struct HomeView: View {
    @StateObject private var viewModel = HomeViewModel()
    @EnvironmentObject var authService: AuthService
    @State private var selectedTimeframe: TimeFrame = .oneWeek
    @State private var showingAddBet = false
    @State private var selectedBet: BetWithGameInfo?
    @State private var showingBetSlip = false
    
    var body: some View {
        NavigationView {
            ScrollView {
                if viewModel.isLoading {
                    ProgressView("Loading your data...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .padding()
                } else if let errorMessage = viewModel.errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.largeTitle)
                            .foregroundColor(.orange)
                        
                        Text("Error Loading Data")
                            .font(.headline)
                        
                        Text(errorMessage)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                        
                        Button("Try Again") {
                            viewModel.refreshData()
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding()
                } else {
                    VStack(spacing: 20) {
                        // Portfolio Performance Chart
                        portfolioChartSection
                        
                        // Quick Actions
                        quickActionsSection
                        
                        // Tracked Bets Section
                        trackedBetsSection
                        
                        // Historical Bets Section
                        historicalBetsSection
                    }
                    .padding()
                }
            }
            .navigationTitle("Home")
            .sheet(isPresented: $showingAddBet) {
                AddBetView()
            }
            .sheet(isPresented: $showingBetSlip) {
                if let selectedBet = selectedBet {
                    TrackedBetSlipView(bet: selectedBet.bet) { // Pass selectedBet.bet instead of selectedBet
                        deleteBet(selectedBet) // Keep selectedBet for the delete function
                    }
                }
            }
            .refreshable {
                viewModel.refreshData()
            }
        }
        .onAppear {
            viewModel.loadData()
        }
    }
    
    // MARK: - Portfolio Chart Section
    private var portfolioChartSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Portfolio Performance")
                    .font(.headline)
                    .fontWeight(.semibold)
                Spacer()
            }
            
            // Overall P&L Display
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Total P&L")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(viewModel.totalPnLFormatted)
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(viewModel.totalPnL >= 0 ? .green : .red)
                }
                
                HStack {
                    Text("ROI")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(viewModel.roiFormatted)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(viewModel.totalPnL >= 0 ? .green : .red)
                }
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
            
            // Time Frame Selector
            HStack {
                ForEach(TimeFrame.allCases, id: \.self) { timeframe in
                    Button(action: {
                        selectedTimeframe = timeframe
                        viewModel.updateChartData(for: timeframe)
                    }) {
                        Text(timeframe.displayName)
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(selectedTimeframe == timeframe ? .white : .primary)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(selectedTimeframe == timeframe ? Color.blue : Color(.systemGray5))
                            .cornerRadius(8)
                    }
                }
            }
            
            // Chart
            Chart(viewModel.chartData) { dataPoint in
                LineMark(
                    x: .value("Date", dataPoint.date),
                    y: .value("P&L", dataPoint.pnl)
                )
                .foregroundStyle(viewModel.totalPnL >= 0 ? .green : .red)
                .interpolationMethod(.catmullRom)
            }
            .frame(height: 200)
            .chartXAxis {
                AxisMarks(values: .automatic) { value in
                    AxisGridLine()
                    AxisValueLabel(format: .dateTime.month(.abbreviated).day())
                }
            }
            .chartYAxis {
                AxisMarks { value in
                    AxisGridLine()
                    AxisValueLabel {
                        if let doubleValue = value.as(Double.self) {
                            Text(formatCurrency(doubleValue))
                        }
                    }
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
    
    // MARK: - Quick Actions Section
    private var quickActionsSection: some View {
        HStack(spacing: 16) {
            Button(action: {
                showingAddBet = true
            }) {
                HStack {
                    Image(systemName: "plus.circle.fill")
                    Text("Add Bet")
                }
                .font(.headline)
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue)
                .cornerRadius(12)
            }
            
            NavigationLink(destination: BetHistoryView()) {
                HStack {
                    Image(systemName: "clock.fill")
                    Text("History")
                }
                .font(.headline)
                .foregroundColor(.blue)
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue.opacity(0.1))
                .cornerRadius(12)
            }
        }
    }
    
    // MARK: - Tracked Bets Section
    private var trackedBetsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Tracked Bets")
                    .font(.headline)
                    .fontWeight(.semibold)
                Spacer()
                NavigationLink("See All", destination: TrackedBetsView())
                    .font(.subheadline)
                    .foregroundColor(.blue)
            }
            
            if viewModel.trackedBets.isEmpty {
                Text("No tracked bets")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding()
            } else {
                ForEach(viewModel.trackedBets.prefix(3)) { bet in
                    TrackedBetRowView(bet: bet) {
                        selectedBet = bet
                        showingBetSlip = true
                    }
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
    
    // MARK: - Historical Bets Section
    private var historicalBetsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Recent Bets")
                    .font(.headline)
                    .fontWeight(.semibold)
                Spacer()
                NavigationLink("See All", destination: BetHistoryView())
                    .font(.subheadline)
                    .foregroundColor(.blue)
            }
            
            if viewModel.recentBets.isEmpty {
                Text("No recent bets")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding()
            } else {
                ForEach(viewModel.recentBets.prefix(5)) { bet in
                    HistoricalBetRowView(bet: bet) {
                        selectedBet = bet
                        showingBetSlip = true
                    }
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
    
    // MARK: - Delete Bet Function
    private func deleteBet(_ betWithGameInfo: BetWithGameInfo) {
        Task {
            await viewModel.deleteBet(betWithGameInfo)
        }
    }
    
    // MARK: - Helper Functions
    private func formatCurrency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencySymbol = "$"
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: value)) ?? "$0"
    }
}

// MARK: - Supporting Views
struct TrackedBetRowView: View {
    let bet: BetWithGameInfo
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 8) {
                // Game matchup header
                HStack {
                    Text(bet.gameMatchup)
                        .font(.caption)
                        .foregroundColor(.blue)
                        .fontWeight(.medium)
                    
                    Spacer()
                    
                    Text(bet.formattedGameDate)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                // Bet details
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(bet.bet.selection)
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(.primary)
                        
                        HStack(spacing: 8) {
                            Text(bet.bet.type.rawValue.capitalized)
                                .font(.caption)
                                .foregroundColor(.secondary)
                            
                            Circle()
                                .fill(Color(.systemGray4))
                                .frame(width: 3, height: 3)
                            
                            Text("$\(Int(bet.bet.amount))")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Spacer()
                    
                    VStack(alignment: .trailing, spacing: 4) {
                        Text(formatOdds(bet.bet.odds))
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(.primary)
                        
                        HStack(spacing: 6) {
                            Circle()
                                .fill(bet.bet.result == .pending ? Color.orange :
                                      bet.bet.result == .won ? Color.green :
                                      bet.bet.result == .lost ? Color.red : Color.gray)
                                .frame(width: 8, height: 8)
                            
                            Text(bet.bet.result.rawValue.capitalized)
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Image(systemName: "chevron.right")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
            .background(Color(.systemGray6))
            .cornerRadius(8)
        }
        .buttonStyle(PlainButtonStyle())
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
}

struct HistoricalBetRowView: View {
    let bet: BetWithGameInfo
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 8) {
                // Game matchup header
                HStack {
                    Text(bet.gameMatchup)
                        .font(.caption)
                        .foregroundColor(.blue)
                        .fontWeight(.medium)
                    
                    Spacer()
                    
                    Text(bet.formattedGameDate)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                // Bet details
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(bet.bet.selection)
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(.primary)
                        
                        HStack(spacing: 8) {
                            Text(bet.bet.type.rawValue.capitalized)
                                .font(.caption)
                                .foregroundColor(.secondary)
                            
                            Circle()
                                .fill(Color(.systemGray4))
                                .frame(width: 3, height: 3)
                            
                            Text("$\(Int(bet.bet.amount))")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Spacer()
                    
                    VStack(alignment: .trailing, spacing: 4) {
                        Text(formatOdds(bet.bet.odds))
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundColor(.primary)
                        
                        if bet.bet.result != .pending {
                            Text(pnlText(for: bet.bet))
                                .font(.caption)
                                .fontWeight(.medium)
                                .foregroundColor(bet.bet.result == .won ? .green :
                                               bet.bet.result == .lost ? .red : .gray)
                        } else {
                            HStack(spacing: 6) {
                                Circle()
                                    .fill(Color.orange)
                                    .frame(width: 8, height: 8)
                                
                                Text("Pending")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                    
                    Image(systemName: "chevron.right")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
            .background(Color(.systemGray6))
            .cornerRadius(8)
        }
        .buttonStyle(PlainButtonStyle())
    }
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
    
    // CORRECTED P&L calculation
        private func pnlText(for bet: Bet) -> String {
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
                return "+$\(Int(winnings))" // Show just the profit
            case .lost:
                return "-$\(Int(bet.amount))" // Show the amount lost
            case .push:
                return "$0"
            case .pending:
                return "Pending"
            }
        }
    private func calculatePayout(amount: Double, odds: Double) -> Double {
        if odds > 0 {
            return amount * (odds / 100) + amount
        } else {
            return amount * (100 / abs(odds)) + amount
        }
    }
}

// MARK: - Time Frame Enum
enum TimeFrame: String, CaseIterable {
    case oneDay = "1D"
    case oneWeek = "1W"
    case oneMonth = "1M"
    case threeMonths = "3M"
    case ytd = "YTD"
    case allTime = "All"
    
    var displayName: String {
        return self.rawValue
    }
}

// MARK: - Chart Data Point
struct ChartDataPoint: Identifiable {
    let id = UUID()
    let date: Date
    let pnl: Double
}

// MARK: - Placeholder Views
struct AddBetView: View {
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationView {
            VStack {
                Text("Add Bet Form")
                Text("(Feature coming soon)")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .navigationTitle("Add Bet")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }
}

struct BetHistoryView: View {
    var body: some View {
        VStack {
            Text("Bet History")
            Text("(Feature coming soon)")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .navigationTitle("Bet History")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct TrackedBetsView: View {
    var body: some View {
        VStack {
            Text("Tracked Bets")
            Text("(Feature coming soon)")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .navigationTitle("Tracked Bets")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    HomeView()
        .environmentObject(AuthService())
}

