//
//  TeamGameDetailView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 11/25/25.
//  Displays game details with prediction-style layout
//

import SwiftUI
import Firebase

struct TeamGameDetailView: View {
    let game: TeamGame
    let team: Team
    @StateObject private var viewModel: TeamGameDetailViewModel
    
    init(game: TeamGame, team: Team) {
        self.game = game
        self.team = team
        _viewModel = StateObject(wrappedValue: TeamGameDetailViewModel(game: game))
    }
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                gameHeaderSection
                
                if let result = game.gameResult {
                    scoreSection(result: result)
                }
                
                gameInfoSection
                
                // Show betting lines if game hasn't started and lines are available
                if game.gameTime > Date(), let betSlip = viewModel.betSlip {
                    bettingLinesSection(betSlip: betSlip)
                }
                
                Spacer()
            }
            .padding()
        }
        .navigationTitle("Game Details")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await viewModel.loadBettingLines()
        }
    }
    
    // MARK: - Game Header Section
    private var gameHeaderSection: some View {
        VStack(spacing: 20) {
            VStack(spacing: 8) {
                TeamLogoView(team: game.awayTeam, size: 80)
                
                Text(game.awayTeam.name)
                    .font(.title2)
                    .fontWeight(.bold)
                
                Text("\(game.awayTeam.record.wins)-\(game.awayTeam.record.losses)")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                if let ranking = game.awayRanking {
                    Text("#\(ranking)")
                        .font(.subheadline)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 4)
                        .background(Color.orange)
                        .cornerRadius(6)
                }
            }
            
            Text(game.neutralSite ? "vs" : "@")
                .font(.title3)
                .fontWeight(.semibold)
                .foregroundColor(.secondary)
            
            VStack(spacing: 8) {
                TeamLogoView(team: game.homeTeam, size: 80)
                
                Text(game.homeTeam.name)
                    .font(.title2)
                    .fontWeight(.bold)
                
                Text("\(game.homeTeam.record.wins)-\(game.homeTeam.record.losses)")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                if let ranking = game.homeRanking {
                    Text("#\(ranking)")
                        .font(.subheadline)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 4)
                        .background(Color.orange)
                        .cornerRadius(6)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.05), radius: 4)
    }
    
    // MARK: - Score Section
    private func scoreSection(result: GameResult) -> some View {
        VStack(spacing: 12) {
            Text("Final Score")
                .font(.headline)
                .foregroundColor(.secondary)
            
            HStack(spacing: 40) {
                VStack(spacing: 4) {
                    Text(game.awayTeam.shortName)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    
                    Text("\(result.awayScore)")
                        .font(.system(size: 48, weight: .bold))
                        .foregroundColor(result.awayScore > result.homeScore ? .green : .primary)
                }
                
                Text("-")
                    .font(.title)
                    .foregroundColor(.secondary)
                
                VStack(spacing: 4) {
                    Text(game.homeTeam.shortName)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    
                    Text("\(result.homeScore)")
                        .font(.system(size: 48, weight: .bold))
                        .foregroundColor(result.homeScore > result.awayScore ? .green : .primary)
                }
            }
            
            Text(result.winner == "home" ? "\(game.homeTeam.shortName) wins" : "\(game.awayTeam.shortName) wins")
                .font(.title3)
                .fontWeight(.semibold)
                .foregroundColor(.green)
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(16)
    }
    
    // MARK: - Game Info Section
    private var gameInfoSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Game Information")
                .font(.headline)
                .fontWeight(.bold)
            
            InfoRow(
                icon: "calendar",
                label: "Date & Time",
                value: game.formattedGameTime
            )
            
            if game.neutralSite {
                InfoRow(
                    icon: "location.fill",
                    label: "Location",
                    value: "Neutral Site"
                )
            } else {
                InfoRow(
                    icon: "house.fill",
                    label: "Location",
                    value: "\(game.homeTeam.shortName) (Home)"
                )
            }
            
            if game.homeConference == game.awayConference {
                InfoRow(
                    icon: "shield.fill",
                    label: "Conference",
                    value: game.homeConference ?? "Unknown"
                )
            } else {
                VStack(spacing: 8) {
                    InfoRow(
                        icon: "shield.fill",
                        label: "\(game.awayTeam.shortName) Conference",
                        value: game.awayConference ?? "Unknown"
                    )
                    
                    InfoRow(
                        icon: "shield.fill",
                        label: "\(game.homeTeam.shortName) Conference",
                        value: game.homeConference ?? "Unknown"
                    )
                }
            }
            
            if game.gameResult != nil {
                InfoRow(
                    icon: "checkmark.circle.fill",
                    label: "Status",
                    value: "Final",
                    valueColor: .green
                )
            } else {
                InfoRow(
                    icon: "clock.fill",
                    label: "Status",
                    value: "Upcoming",
                    valueColor: .blue
                )
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.05), radius: 4)
    }
    
    // MARK: - Betting Lines Section (Optional)
    private func bettingLinesSection(betSlip: BetSlip) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Betting Lines Available")
                .font(.headline)
                .fontWeight(.bold)
            
            Text("View complete betting lines, odds comparison, and our predictions for this game.")
                .font(.subheadline)
                .foregroundColor(.secondary)
            
            // Navigate directly to PredictionDetailView
            NavigationLink(destination: predictionDetailView(betSlip: betSlip)) {
                HStack {
                    Image(systemName: "chart.bar.fill")
                    Text("View Betting Lines & Predictions")
                        .fontWeight(.semibold)
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(12)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.05), radius: 4)
    }
    
    // Helper to create PredictionDetailView from BetSlip
    @ViewBuilder
    private func predictionDetailView(betSlip: BetSlip) -> some View {
        // Create a PredictionGame from the BetSlip
        let predictionGame = createPredictionGame(from: betSlip)
        
        // Need to create a minimal PredictionsViewModel for the detail view
        let predictionsViewModel = PredictionsViewModel()
        
        PredictionDetailView(prediction: predictionGame, viewModel: predictionsViewModel)
    }
    
    // Convert BetSlip to PredictionGame
    private func createPredictionGame(from betSlip: BetSlip) -> PredictionGame {
        // Determine best bet from available lines
        let bestBet = determineBestBet(from: betSlip)
        
        // Extract confidence and key factors
        var keyFactors: [String] = []
        if let homeRank = betSlip.homeRanking {
            keyFactors.append("Home Rank: #\(homeRank)")
        }
        if let awayRank = betSlip.awayRanking {
            keyFactors.append("Away Rank: #\(awayRank)")
        }
        if let homeConf = betSlip.homeConference {
            keyFactors.append("Home: \(homeConf)")
        }
        if let awayConf = betSlip.awayConference {
            keyFactors.append("Away: \(awayConf)")
        }
        
        return PredictionGame(
            homeTeam: betSlip.homeTeam,
            awayTeam: betSlip.awayTeam,
            gameTime: betSlip.gameTime,
            bestBet: bestBet,
            confidence: 50.0,
            analysis: betSlip.predictionInfo?.analysis,
            keyFactors: keyFactors,
            betSlip: betSlip
        )
    }
    
    // Determine the best bet to display
    private func determineBestBet(from betSlip: BetSlip) -> BestBet {
        // Try to use spread as default
        if let firstSpreadKey = betSlip.bettingLines.spread.keys.first,
           let odds = betSlip.bettingLines.spread[firstSpreadKey] {
            return BestBet(
                type: .spread,
                selection: firstSpreadKey,
                odds: odds,
                sportsbook: betSlip.sportsbook
            )
        }
        
        // Fallback to moneyline
        if let firstMoneylineKey = betSlip.bettingLines.moneyline.keys.first,
           let odds = betSlip.bettingLines.moneyline[firstMoneylineKey] {
            return BestBet(
                type: .moneyline,
                selection: firstMoneylineKey,
                odds: odds,
                sportsbook: betSlip.sportsbook
            )
        }
        
        // Fallback to total
        if let firstTotalKey = betSlip.bettingLines.total.keys.first,
           let odds = betSlip.bettingLines.total[firstTotalKey] {
            return BestBet(
                type: .total,
                selection: firstTotalKey,
                odds: odds,
                sportsbook: betSlip.sportsbook
            )
        }
        
        // Ultimate fallback
        return BestBet(
            type: .spread,
            selection: "\(betSlip.homeTeam.shortName) +0.0",
            odds: -110,
            sportsbook: betSlip.sportsbook
        )
    }
}

// MARK: - Team Game Detail ViewModel
@MainActor
class TeamGameDetailViewModel: ObservableObject {
    @Published var betSlip: BetSlip?
    @Published var isLoadingLines = false
    
    private let game: TeamGame
    private let firebaseService = FirebaseService()
    
    init(game: TeamGame) {
        self.game = game
    }
    
    func loadBettingLines() async {
        // Only load betting lines if game hasn't started
        guard game.gameTime > Date() else { return }
        
        isLoadingLines = true
        
        do {
            // Fetch complete bet slip with all lines for this game
            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "yyyy-MM-dd"
            _ = dateFormatter.string(from: game.gameTime)
            
            let betSlips = try await firebaseService.fetchBetSlips(for: game.gameTime)
            
            // Find the bet slip for this game
            if let slip = betSlips.first(where: { $0.gameID == game.gameID }) {
                await MainActor.run {
                    self.betSlip = slip
                    self.isLoadingLines = false
                }
            } else {
                await MainActor.run {
                    self.isLoadingLines = false
                }
            }
        } catch {
            print("❌ Error loading betting lines: \(error)")
            await MainActor.run {
                self.isLoadingLines = false
            }
        }
    }
}

#Preview {
    NavigationView {
        TeamGameDetailView(
            game: TeamGame(
                id: "2025-01-15_game1",
                gameID: "2025-01-15_game1",
                homeTeam: Team(
                    id: "duke",
                    name: "Duke",
                    shortName: "Duke",
                    logoURL: "https://via.placeholder.com/150",
                    record: TeamRecord(wins: 15, losses: 3),
                    conference: "ACC",
                    ranking: 5,
                    colorHex: "#003087"
                ),
                awayTeam: Team(
                    id: "unc",
                    name: "North Carolina",
                    shortName: "UNC",
                    logoURL: "https://via.placeholder.com/150",
                    record: TeamRecord(wins: 14, losses: 4),
                    conference: "ACC",
                    ranking: 8,
                    colorHex: "#7BAFD4"
                ),
                gameTime: Date(),
                tipoffTimeString: "7:00 PM EST",
                neutralSite: false,
                homeConference: "ACC",
                awayConference: "ACC",
                homeRanking: 5,
                awayRanking: 8,
                gameResult: nil
            ),
            team: Team(
                id: "duke",
                name: "Duke",
                shortName: "Duke",
                logoURL: "https://via.placeholder.com/150",
                record: TeamRecord(wins: 15, losses: 3),
                conference: "ACC",
                ranking: 5,
                colorHex: "#003087"
            )
        )
    }
}
