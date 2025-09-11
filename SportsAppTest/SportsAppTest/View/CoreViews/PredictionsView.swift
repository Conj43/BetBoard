//
//  PredictionsView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct PredictionsView: View {
    @StateObject private var viewModel = PredictionsViewModel()
    @EnvironmentObject var authService: AuthService
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                if viewModel.isLoading {
                    ProgressView("Loading predictions...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let errorMessage = viewModel.errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.largeTitle)
                            .foregroundColor(.orange)
                        
                        Text("Error Loading Predictions")
                            .font(.headline)
                        
                        Text(errorMessage)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                        
                        Button("Try Again") {
                            Task {
                                await viewModel.refreshPredictions()
                            }
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding()
                } else {
                    // Header Section
                    headerSection
                    
                    // Bet Type Filter
                    betTypeFilter
                    
                    // Predictions List
                    predictionsList
                }
            }
            .navigationTitle("Predictions")
            .background(Color(.systemGroupedBackground))
            .refreshable {
                Task {
                    await viewModel.refreshPredictions()
                }
            }
        }
        .task {
            await viewModel.loadPredictions()
        }
    }
    
    // MARK: - Header Section
    private var headerSection: some View {
        VStack(spacing: 12) {
            HStack {
                Image(systemName: "brain.head.profile")
                    .font(.title2)
                    .foregroundColor(.purple)
                
                VStack(alignment: .leading, spacing: 4) {
                    Text("Predictions")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Text("Our highest confidence bets")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    Text("Today")
                        .font(.subheadline)
                        .fontWeight(.medium)
                    
                    Text("\(viewModel.filteredPredictions.count) Games")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding()
            .background(Color(.systemBackground))
            .cornerRadius(12)
            .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
        }
        .padding(.horizontal)
        .padding(.top, 8)
    }
    
    // MARK: - Bet Type Filter
    private var betTypeFilter: some View {
        HStack(spacing: 0) {
            ForEach([BetType.moneyline, BetType.spread, BetType.total], id: \.self) { betType in
                Button(action: {
                    viewModel.selectedBetType = betType
                }) {
                    VStack(spacing: 6) {
                        Image(systemName: iconForBetType(betType))
                            .font(.title3)
                        
                        Text(betType.displayName)
                            .font(.subheadline)
                            .fontWeight(.medium)
                    }
                    .foregroundColor(viewModel.selectedBetType == betType ? .white : .primary)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(viewModel.selectedBetType == betType ? Color.purple : Color(.systemGray6))
                    .animation(.easeInOut(duration: 0.2), value: viewModel.selectedBetType)
                }
            }
        }
        .cornerRadius(12)
        .padding(.horizontal)
        .padding(.vertical, 8)
    }
    
    // MARK: - Predictions List
    private var predictionsList: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                if viewModel.filteredPredictions.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "chart.bar.xaxis")
                            .font(.largeTitle)
                            .foregroundColor(.secondary)
                        
                        Text("No predictions available")
                            .font(.headline)
                            .foregroundColor(.secondary)
                        
                        Text("Check back later for AI predictions")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .padding()
                } else {
                    ForEach(viewModel.filteredPredictions) { prediction in
                        NavigationLink(destination: PredictionDetailView(prediction: prediction, viewModel: viewModel)) {
                            PredictionRowView(prediction: prediction)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                }
            }
            .padding(.horizontal)
            .padding(.top, 8)
        }
    }
    
    // MARK: - Helper Functions
    private func iconForBetType(_ betType: BetType) -> String {
        switch betType {
        case .moneyline:
            return "dollarsign.circle"
        case .spread:
            return "chart.line.uptrend.xyaxis"
        case .total:
            return "arrow.up.arrow.down"
        }
    }
}

// MARK: - Prediction Row View
struct PredictionRowView: View {
    let prediction: PredictionGame
    
    var body: some View {
        VStack(spacing: 12) {
            // Game Info Header
            HStack {
                // Away Team
                HStack(spacing: 6) {
                    if let awayRanking = prediction.awayTeam.ranking {
                        Text("#\(awayRanking)")
                            .font(.caption)
                            .fontWeight(.bold)
                            .foregroundColor(.blue)
                    }
                    
                    Text(prediction.awayTeam.shortName)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
                
                Text("@")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                // Home Team
                HStack(spacing: 6) {
                    if let homeRanking = prediction.homeTeam.ranking {
                        Text("#\(homeRanking)")
                            .font(.caption)
                            .fontWeight(.bold)
                            .foregroundColor(.blue)
                    }
                    
                    Text(prediction.homeTeam.shortName)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
                
                Spacer()
                
                // Game Time
                Text(prediction.formattedGameTime)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            // Best Bet Info
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Best Bet")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .textCase(.uppercase)
                    
                    Text(prediction.bestBet.selection)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    Text("(\(prediction.bestBet.sportsbook.displayName))")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Text(formatOdds(prediction.bestBet.odds))
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(.blue)
                }
            }
            
            // Confidence Bar
            HStack {
                Text("Confidence")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                HStack(spacing: 8) {
                    // Confidence Bar
                    GeometryReader { geometry in
                        ZStack(alignment: .leading) {
                            Rectangle()
                                .fill(Color(.systemGray5))
                                .frame(height: 6)
                                .cornerRadius(3)
                            
                            Rectangle()
                                .fill(confidenceColor(for: prediction.confidence))
                                .frame(width: geometry.size.width * CGFloat(prediction.confidence / 100.0), height: 6)
                                .cornerRadius(3)
                        }
                    }
                    .frame(width: 80, height: 6)
                    
                    Text("\(Int(prediction.confidence))%")
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundColor(confidenceColor(for: prediction.confidence))
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
    
    private func confidenceColor(for confidence: Double) -> Color {
        if confidence >= 90 {
            return .green
        } else if confidence >= 80 {
            return .orange
        } else if confidence >= 70 {
            return .yellow
        } else {
            return .red
        }
    }
}

// MARK: - Prediction Detail View
struct PredictionDetailView: View {
    let prediction: PredictionGame
    @ObservedObject var viewModel: PredictionsViewModel
    @State private var showingTrackConfirmation = false
    @State private var trackingInProgress = false
    @State private var trackedBetDetails: String = ""
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Prediction Analysis Header
                predictionAnalysisHeader
                
                // BetSlip UI with amount tracking
                BetSlipUI(betSlip: prediction.betSlip) { betType, selection, odds, amount in
                    trackSpecificBet(betType: betType, selection: selection, odds: odds, amount: amount)
                }
                
                // Additional Analysis
                additionalAnalysisSection
            }
            .padding()
        }
        .background(Color(.systemGroupedBackground))
        .navigationTitle("Prediction Details")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Bet Tracked!", isPresented: $showingTrackConfirmation) {
            Button("OK") { }
        } message: {
            Text("Successfully tracked: \(trackedBetDetails)")
        }
        .disabled(trackingInProgress)
    }
    
    private var predictionAnalysisHeader: some View {
        VStack(spacing: 16) {
            HStack {
                Image(systemName: "brain.head.profile")
                    .font(.title2)
                    .foregroundColor(.purple)
                
                VStack(alignment: .leading, spacing: 4) {
                    Text("Analysis")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Text("Recommended Bet")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    Text("\(Int(prediction.confidence))%")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.purple)
                    
                    Text("Confidence")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            
            if let analysis = prediction.analysis {
                Text(analysis)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.leading)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
    }
    
    private var additionalAnalysisSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Key Factors")
                .font(.headline)
                .fontWeight(.semibold)
            
            ForEach(prediction.keyFactors, id: \.self) { factor in
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.caption)
                        .foregroundColor(.green)
                        .padding(.top, 2)
                    
                    Text(factor)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
    }
    
    private func trackSpecificBet(betType: BetType, selection: String, odds: Double, amount: Double) {
        trackingInProgress = true
        trackedBetDetails = "\(selection) for $\(String(format: "%.2f", amount)) at \(formatOdds(odds))"
        
        Task {
            await viewModel.trackSpecificBet(
                from: prediction,
                betType: betType,
                selection: selection,
                odds: odds,
                amount: amount
            )
            
            await MainActor.run {
                trackingInProgress = false
                if viewModel.errorMessage == nil {
                    showingTrackConfirmation = true
                }
            }
        }
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
}

// MARK: - Supporting Data Models
struct PredictionGame: Identifiable {
    let id = UUID()
    let homeTeam: Team
    let awayTeam: Team
    let gameTime: Date
    let bestBet: BestBet
    let confidence: Double
    let analysis: String?
    let keyFactors: [String]
    let betSlip: BetSlip
    
    var formattedGameTime: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM/dd - h:mm a"
        return formatter.string(from: gameTime)
    }
}

struct BestBet {
    let type: BetType
    let selection: String
    let odds: Double
    let sportsbook: Sportsbook
}

#Preview {
    PredictionsView()
        .environmentObject(AuthService())
}
