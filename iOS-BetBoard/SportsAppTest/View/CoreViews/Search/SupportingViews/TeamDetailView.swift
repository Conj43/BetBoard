//
//  TeamDetailView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 11/25/25.
//  Optimized version with navigation to game details
//

import SwiftUI

struct TeamDetailView: View {
    let team: Team
    @StateObject private var viewModel: TeamDetailViewModel
    
    init(team: Team) {
        self.team = team
        _viewModel = StateObject(wrappedValue: TeamDetailViewModel(team: team))
    }
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                teamHeaderSection
                
                if viewModel.isLoading {
                    ProgressView("Loading games...")
                        .padding()
                } else if let errorMessage = viewModel.errorMessage {
                    errorView(errorMessage: errorMessage)
                } else if viewModel.upcomingGames.isEmpty && viewModel.completedGames.isEmpty {
                    noGamesView
                } else {
                    gamesSection
                }
            }
            .padding()
        }
        .navigationTitle(team.shortName)
        .navigationBarTitleDisplayMode(.inline)
        .refreshable {
            await viewModel.loadGames()
        }
        .task {
            await viewModel.loadGames()
        }
    }
    
    // MARK: - Team Header Section
    private var teamHeaderSection: some View {
        VStack(spacing: 16) {
            TeamLogoView(team: team, size: 100)
            
            Text(team.name)
                .font(.title2)
                .fontWeight(.bold)
            
            HStack(spacing: 20) {
                
                VStack {
                    Text("Conference")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(team.conference)
                        .font(.title3)
                        .fontWeight(.semibold)
                }
                
                if let ranking = team.ranking {
                    Divider()
                        .frame(height: 40)
                    
                    VStack {
                        Text("Rank")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Text("#\(ranking)")
                            .font(.title3)
                            .fontWeight(.semibold)
                            .foregroundColor(.orange)
                    }
                }
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.05), radius: 4)
    }
    
    // MARK: - Games Section
    private var gamesSection: some View {
        VStack(spacing: 16) {
            if !viewModel.upcomingGames.isEmpty {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Image(systemName: "calendar")
                            .foregroundColor(.blue)
                        Text("Upcoming Games")
                            .font(.headline)
                            .fontWeight(.bold)
                    }
                    
                    ForEach(viewModel.upcomingGames) { game in
                        NavigationLink(destination: TeamGameDetailView(game: game, team: team)) {
                            TeamGameRowView(game: game, team: team)
                        }
                    }
                }
            }
            
            if !viewModel.completedGames.isEmpty {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                        Text("Recent Games")
                            .font(.headline)
                            .fontWeight(.bold)
                    }
                    
                    ForEach(viewModel.completedGames) { game in
                        NavigationLink(destination: TeamGameDetailView(game: game, team: team)) {
                            TeamGameRowView(game: game, team: team)
                        }
                    }
                }
            }
        }
    }
    
    // MARK: - Error View
    private func errorView(errorMessage: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.largeTitle)
                .foregroundColor(.orange)
            
            Text("Error Loading Games")
                .font(.headline)
            
            Text(errorMessage)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            
            Button("Try Again") {
                Task {
                    await viewModel.loadGames()
                }
            }
            .buttonStyle(.bordered)
        }
        .padding()
    }
    
    // MARK: - No Games View
    private var noGamesView: some View {
        VStack(spacing: 16) {
            Image(systemName: "calendar.badge.exclamationmark")
                .font(.system(size: 60))
                .foregroundColor(.secondary)
            
            Text("No Games Found")
                .font(.headline)
            
            Text("No games scheduled for \(team.shortName)")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
    }
}

// MARK: - Team Game Row View
struct TeamGameRowView: View {
    let game: TeamGame
    let team: Team
    @StateObject private var viewModel: TeamGameRowViewModel
    
    init(game: TeamGame, team: Team) {
        self.game = game
        self.team = team
        _viewModel = StateObject(wrappedValue: TeamGameRowViewModel(game: game))
    }
    
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(isHomeGame ? "vs" : "@")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Text(opponentTeam.shortName)
                            .font(.headline)
                            .fontWeight(.semibold)
                    }
                    
                    Text(opponentTeam.conference)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                TeamLogoView(team: opponentTeam, size: 40)
                
                Spacer()
                
                VStack(alignment: .trailing, spacing: 4) {
                    if viewModel.isCompleted, let result = viewModel.gameResult {
                        Text(scoreText(result: result))
                            .font(.headline)
                            .fontWeight(.bold)
                            .foregroundColor(didTeamWin(result: result) ? .green : .red)
                        
                        Text(resultText(result: result))
                            .font(.caption)
                            .foregroundColor(didTeamWin(result: result) ? .green : .red)
                    } else {
                        Text(game.formattedGameTime)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                }
            }
            
            HStack(spacing: 8) {
                if game.neutralSite {
                    Label("Neutral", systemImage: "location.fill")
                        .font(.caption)
                        .foregroundColor(.orange)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.orange.opacity(0.1))
                        .cornerRadius(6)
                }
                
                if let ranking = opponentTeam.ranking {
                    Text("#\(ranking)")
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.orange)
                        .cornerRadius(6)
                }
                
                Spacer()
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
    }
    
    private var isHomeGame: Bool {
        game.homeTeam.id == team.id
    }
    
    private var opponentTeam: Team {
        isHomeGame ? game.awayTeam : game.homeTeam
    }
    
    private func scoreText(result: GameResult) -> String {
        if isHomeGame {
            return "\(result.homeScore) - \(result.awayScore)"
        } else {
            return "\(result.awayScore) - \(result.homeScore)"
        }
    }
    
    private func didTeamWin(result: GameResult) -> Bool {
        if isHomeGame {
            return result.homeScore > result.awayScore
        } else {
            return result.awayScore > result.homeScore
        }
    }
    
    private func resultText(result: GameResult) -> String {
        didTeamWin(result: result) ? "W" : "L"
    }
}

#Preview {
    NavigationView {
        TeamDetailView(team: Team(
            id: "duke",
            name: "Duke",
            shortName: "Duke",
            logoURL: "https://via.placeholder.com/150",
            record: TeamRecord(wins: 20, losses: 5),
            conference: "ACC",
            ranking: 5,
            colorHex: "#003087"
        ))
    }
}
