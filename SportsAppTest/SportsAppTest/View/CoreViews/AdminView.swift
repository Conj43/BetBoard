//
//  AdminView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/27/25.
//

import SwiftUI

struct AdminView: View {
    @StateObject private var gameUpdater = GameResultUpdater()
    @State private var selectedGame: Game?
    @State private var homeScore: String = ""
    @State private var awayScore: String = ""
    @State private var showingGamePicker = false
    @State private var showingConfirmation = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                // Header
                VStack(spacing: 12) {
                    Image(systemName: "gearshape.fill")
                        .font(.largeTitle)
                        .foregroundColor(.orange)
                    
                    Text("Game Results Admin")
                        .font(.title)
                        .fontWeight(.bold)
                    
                    Text("Update game results to test bet outcomes")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                .padding(.top)
                
                // Game Selection
                VStack(alignment: .leading, spacing: 12) {
                    Text("Select Game")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Button(action: {
                        showingGamePicker = true
                    }) {
                        HStack {
                            if let game = selectedGame {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("\(game.awayTeam) @ \(game.homeTeam)")
                                        .font(.subheadline)
                                        .fontWeight(.medium)
                                        .foregroundColor(.primary)
                                    
                                    Text(game.formattedDate)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            } else {
                                Text("Choose a game to update")
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)
                            }
                            
                            Spacer()
                            
                            Image(systemName: "chevron.down")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                    }
                }
                
                // Score Input
                if selectedGame != nil {
                    VStack(alignment: .leading, spacing: 16) {
                        Text("Final Score")
                            .font(.headline)
                            .fontWeight(.semibold)
                        
                        HStack(spacing: 20) {
                            // Away Team Score
                            VStack(spacing: 8) {
                                Text(selectedGame?.awayTeam ?? "Away")
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                
                                TextField("0", text: $awayScore)
                                    .font(.title)
                                    .fontWeight(.bold)
                                    .keyboardType(.numberPad)
                                    .textFieldStyle(RoundedBorderTextFieldStyle())
                                    .multilineTextAlignment(.center)
                            }
                            
                            Text("@")
                                .font(.title2)
                                .foregroundColor(.secondary)
                            
                            // Home Team Score
                            VStack(spacing: 8) {
                                Text(selectedGame?.homeTeam ?? "Home")
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                                
                                TextField("0", text: $homeScore)
                                    .font(.title)
                                    .fontWeight(.bold)
                                    .keyboardType(.numberPad)
                                    .textFieldStyle(RoundedBorderTextFieldStyle())
                                    .multilineTextAlignment(.center)
                            }
                        }
                    }
                }
                
                // Update Status
                if let message = gameUpdater.updateMessage {
                    Text(message)
                        .font(.subheadline)
                        .foregroundColor(message.contains("Success") ? .green : .red)
                        .multilineTextAlignment(.center)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                }
                
                Spacer()
                
                // Action Buttons
                VStack(spacing: 12) {
                    if gameUpdater.isUpdating {
                        ProgressView("Updating game result...")
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(.systemGray6))
                            .cornerRadius(12)
                    } else {
                        Button(action: {
                            showingConfirmation = true
                        }) {
                            Text("Update Game Result")
                                .font(.headline)
                                .fontWeight(.semibold)
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(canUpdate ? Color.orange : Color.gray)
                                .cornerRadius(12)
                        }
                        .disabled(!canUpdate)
                    }
                    
                    // Debug Calculator Button
                    NavigationLink(destination: DebugBetCalculatorView()) {
                        Text("Debug Bet Calculator")
                            .font(.subheadline)
                            .foregroundColor(.blue)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.blue.opacity(0.1))
                            .cornerRadius(12)
                    }
                    
                    // Quick Test Buttons
                    HStack(spacing: 12) {
                        Button("Duke Wins") {
                            homeScore = "75"
                            awayScore = "68"
                        }
                        .font(.subheadline)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(Color.blue.opacity(0.1))
                        .foregroundColor(.blue)
                        .cornerRadius(20)
                        
                        Button("UNC Wins") {
                            homeScore = "68"
                            awayScore = "75"
                        }
                        .font(.subheadline)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(Color.blue.opacity(0.1))
                        .foregroundColor(.blue)
                        .cornerRadius(20)
                    }
                }
            }
            .padding()
            .navigationTitle("Admin")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(isPresented: $showingGamePicker) {
                GamePickerView(
                    games: gameUpdater.availableGames,
                    selectedGame: $selectedGame
                )
            }
            .alert("Confirm Update", isPresented: $showingConfirmation) {
                Button("Cancel", role: .cancel) { }
                Button("Update", role: .destructive) {
                    updateGameResult()
                }
            } message: {
                Text("Are you sure you want to update the game result? This will affect all tracked bets for this game.")
            }
        }
        .task {
            await gameUpdater.loadAvailableGames()
        }
    }
    
    private var canUpdate: Bool {
        selectedGame != nil &&
        !homeScore.isEmpty &&
        !awayScore.isEmpty &&
        Int(homeScore) != nil &&
        Int(awayScore) != nil
    }
    
    private func updateGameResult() {
        guard let game = selectedGame,
              let home = Int(homeScore),
              let away = Int(awayScore) else { return }
        
        Task {
            await gameUpdater.updateGameResult(
                gameID: game.id,
                homeScore: home,
                awayScore: away
            )
        }
    }
}

// MARK: - Game Picker View
struct GamePickerView: View {
    let games: [Game]
    @Binding var selectedGame: Game?
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationView {
            List(games) { game in
                Button(action: {
                    selectedGame = game
                    dismiss()
                }) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("\(game.awayTeam) @ \(game.homeTeam)")
                            .font(.headline)
                            .fontWeight(.medium)
                            .foregroundColor(.primary)
                        
                        HStack {
                            Text(game.formattedDate)
                                .font(.caption)
                                .foregroundColor(.secondary)
                            
                            Spacer()
                            
                            Text(game.scoreText)
                                .font(.caption)
                                .fontWeight(.medium)
                                .foregroundColor(.blue)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
            .navigationTitle("Select Game")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }
}

#Preview {
    AdminView()
}
