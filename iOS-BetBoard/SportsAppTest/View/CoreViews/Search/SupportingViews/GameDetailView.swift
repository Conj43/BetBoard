//
//  GameDetailView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 11/25/25.
//


import Firebase
import SwiftUI

struct GameDetailView: View {
    let betSlip: BetSlip
    @StateObject private var viewModel: GameDetailViewModel
    
    init(betSlip: BetSlip) {
        self.betSlip = betSlip
        _viewModel = StateObject(wrappedValue: GameDetailViewModel(betSlip: betSlip))
    }
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Game Header
                gameHeaderSection
                
                // Score Section (if completed)
                if let result = viewModel.gameResult {
                    scoreSection(result: result)
                }
                
                // Game Info
                gameInfoSection
                
                Spacer()
            }
            .padding()
        }
        .navigationTitle("Game Details")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await viewModel.loadGameResult()
        }
    }
    
    // MARK: - Game Header Section
    private var gameHeaderSection: some View {
        VStack(spacing: 20) {
            // Away Team
            VStack(spacing: 8) {
                TeamLogoView(team: betSlip.awayTeam, size: 80)
                
                Text(betSlip.awayTeam.name)
                    .font(.title2)
                    .fontWeight(.bold)
                
                Text("\(betSlip.awayTeam.record.wins)-\(betSlip.awayTeam.record.losses)")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                if let ranking = betSlip.awayRanking {
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
            
            // VS/@ indicator
            Text(betSlip.neutralSite ? "vs" : "@")
                .font(.title3)
                .fontWeight(.semibold)
                .foregroundColor(.secondary)
            
            // Home Team
            VStack(spacing: 8) {
                TeamLogoView(team: betSlip.homeTeam, size: 80)
                
                Text(betSlip.homeTeam.name)
                    .font(.title2)
                    .fontWeight(.bold)
                
                Text("\(betSlip.homeTeam.record.wins)-\(betSlip.homeTeam.record.losses)")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                if let ranking = betSlip.homeRanking {
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
                // Away Score
                VStack(spacing: 4) {
                    Text(betSlip.awayTeam.shortName)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    
                    Text("\(result.awayScore)")
                        .font(.system(size: 48, weight: .bold))
                        .foregroundColor(result.awayScore > result.homeScore ? .green : .primary)
                }
                
                Text("-")
                    .font(.title)
                    .foregroundColor(.secondary)
                
                // Home Score
                VStack(spacing: 4) {
                    Text(betSlip.homeTeam.shortName)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    
                    Text("\(result.homeScore)")
                        .font(.system(size: 48, weight: .bold))
                        .foregroundColor(result.homeScore > result.awayScore ? .green : .primary)
                }
            }
            
            // Winner indicator
            Text(result.winner == "home" ? "\(betSlip.homeTeam.shortName) wins" : "\(betSlip.awayTeam.shortName) wins")
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
            
            // Game Time
            InfoRow(
                icon: "calendar",
                label: "Date & Time",
                value: betSlip.formattedGameTime
            )
            
            // Location
            if betSlip.neutralSite {
                InfoRow(
                    icon: "location.fill",
                    label: "Location",
                    value: "Neutral Site"
                )
            } else {
                InfoRow(
                    icon: "house.fill",
                    label: "Location",
                    value: "\(betSlip.homeTeam.shortName) (Home)"
                )
            }
            
            // Conferences
            if betSlip.homeConference == betSlip.awayConference {
                InfoRow(
                    icon: "shield.fill",
                    label: "Conference",
                    value: betSlip.homeConference ?? "Unknown"
                )
            } else {
                VStack(spacing: 8) {
                    InfoRow(
                        icon: "shield.fill",
                        label: "\(betSlip.awayTeam.shortName) Conference",
                        value: betSlip.awayConference ?? "Unknown"
                    )
                    
                    InfoRow(
                        icon: "shield.fill",
                        label: "\(betSlip.homeTeam.shortName) Conference",
                        value: betSlip.homeConference ?? "Unknown"
                    )
                }
            }
            
            // Status
            if viewModel.isCompleted {
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
}

// MARK: - Info Row Component
struct InfoRow: View {
    let icon: String
    let label: String
    let value: String
    var valueColor: Color = .primary
    
    var body: some View {
        HStack {
            Image(systemName: icon)
                .font(.caption)
                .foregroundColor(.blue)
                .frame(width: 20)
            
            Text(label)
                .font(.subheadline)
                .foregroundColor(.secondary)
            
            Spacer()
            
            Text(value)
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundColor(valueColor)
        }
    }
}

// MARK: - Game Detail ViewModel
@MainActor
class GameDetailViewModel: ObservableObject {
    @Published var gameResult: GameResult?
    @Published var isCompleted = false
    
    private let betSlip: BetSlip
    
    init(betSlip: BetSlip) {
        self.betSlip = betSlip
        self.isCompleted = betSlip.gameTime < Date()
    }
    
    func loadGameResult() async {
        guard isCompleted else { return }
        
        do {
            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "yyyy-MM-dd"
            let dateStr = dateFormatter.string(from: betSlip.gameTime)
            
            print("🔍 Loading game result for \(betSlip.gameID)...")
            
            let resultsDoc = try await Firestore.firestore()
                .collection("games")
                .document(dateStr)
                .collection("games")
                .document(betSlip.gameID)
                .collection("game_results")
                .document("odds_api")
                .getDocument()
            
            if resultsDoc.exists,
               let resultData = resultsDoc.data(),
               let completed = resultData["completed"] as? Bool,
               completed,
               let homeScore = resultData["home_score"] as? Int,
               let awayScore = resultData["away_score"] as? Int {
                
                await MainActor.run {
                    self.gameResult = GameResult(
                        homeScore: homeScore,
                        awayScore: awayScore,
                        homeTeam: betSlip.homeTeam.shortName,
                        awayTeam: betSlip.awayTeam.shortName
                    )
                }
                
                print("✅ Loaded result: \(betSlip.awayTeam.shortName) \(awayScore) @ \(betSlip.homeTeam.shortName) \(homeScore)")
            }
        } catch {
            print("❌ Error loading game result: \(error)")
        }
    }
}

#Preview {
    NavigationView {
        GameDetailView(betSlip: BetSlip(
            id: "2025-01-15_game1",
            gameID: "2025-01-15_game1",
            sportsbook: .draftkings,
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
            bettingLines: BettingLines.create(id: "test", gameID: "test", moneyline: [:], spread: [:], total: [:]),
            allBettingLines: nil,
            predictionInfo: nil,
            neutralSite: false,
            homeConference: "ACC",
            awayConference: "ACC",
            homeRanking: 5,
            awayRanking: 8
        ))
    }
}
