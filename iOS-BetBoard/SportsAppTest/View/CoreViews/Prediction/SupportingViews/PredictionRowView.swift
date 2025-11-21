//
//  PredictionRowView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import SwiftUI

struct PredictionRowView: View {
    let prediction: PredictionGame
    @EnvironmentObject var predictionsViewModel: PredictionsViewModel
    
    // Check if we're in recommended mode
    private var isRecommended: Bool {
        predictionsViewModel.viewMode == .recommended
    }
    
    // Get game result
    private var gameResult: GameResult? {
        predictionsViewModel.gameResults[prediction.betSlip.gameID]
    }
    
    // Check if bet won
    private var betResult: Bool? {
        guard let result = gameResult else { return nil }
        
        // Extract line from bestBet selection if needed
        let line: Double?
        if prediction.bestBet.type == .spread {
            // Parse "Team Name +7.5" or "Team Name -7.5"
            let components = prediction.bestBet.selection.components(separatedBy: " ")
            if let lastComponent = components.last,
               let lineValue = Double(lastComponent.replacingOccurrences(of: "+", with: "")) {
                line = lineValue
            } else {
                line = nil
            }
        } else if prediction.bestBet.type == .total {
            // Get line from key factors
            if let lineFactor = prediction.keyFactors.first(where: { $0.contains("Book Line:") }) {
                let lineStr = lineFactor.replacingOccurrences(of: "Book Line:", with: "").trimmingCharacters(in: .whitespaces)
                line = Double(lineStr)
            } else {
                line = nil
            }
        } else {
            line = nil
        }
        
        return result.didBetWin(
            betType: prediction.bestBet.type,
            selection: prediction.bestBet.selection,
            line: line
        )
    }
    
    // Get win probability from key factors
    private var winProbability: Double {
        if let probFactor = prediction.keyFactors.first(where: { $0.starts(with: "Win Probability:") }) {
            let probString = probFactor.dropFirst(16).dropLast(1).trimmingCharacters(in: .whitespaces)
            return Double(probString) ?? 0.0
        }
        return 0.0
    }
    
    // Get edge strength from key factors
    private var edgeStrength: Double {
        if let edgeFactor = prediction.keyFactors.first(where: { $0.starts(with: "Edge Strength:") }) {
            let edgeString = edgeFactor.dropFirst(15).trimmingCharacters(in: .whitespaces)
            return Double(edgeString) ?? 0.0
        }
        return 0.0
    }
    
    var body: some View {
        VStack(spacing: 0) {
            // Game header with team info
            gameHeaderView
            
            // Prediction details (only for recommended games)
            if isRecommended {
                predictionDetailsView
            }
        }
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.gray.opacity(0.2), lineWidth: 1)
        )
        .padding(.bottom, 4)
    }
    
    private var gameHeaderView: some View {
        VStack(spacing: 8) {
            HStack {
                // Game date - tipoff time
                Text(formattedDateAndTime)
                    .font(.footnote)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                // Show result if game is complete
                if let result = gameResult {
                    VStack(spacing: 2) {
                        HStack(spacing: 4) {
                            Text("Final: \(result.finalScore)")
                                .font(.caption)
                                .fontWeight(.semibold)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.blue.opacity(0.2))
                        .foregroundColor(.blue)
                        .cornerRadius(8)
                        
                        // Show bet result (only for recommended)
                        if isRecommended, let won = betResult {
                            HStack(spacing: 2) {
                                Image(systemName: won ? "checkmark.circle.fill" : "xmark.circle.fill")
                                    .font(.caption2)
                                Text(won ? "WON" : "LOST")
                                    .font(.caption2)
                                    .fontWeight(.bold)
                            }
                            .foregroundColor(won ? .green : .red)
                        }
                    }
                } else if isRecommended {
                    EmptyView()
                }
            }
            
            // Team matchup
            HStack(alignment: .center, spacing: 8) {
                // Away team
                TeamLogoView(team: prediction.awayTeam, size: 32)
                
                VStack(spacing: 2) {
                    HStack(spacing: 4) {
                        Text(prediction.awayTeam.shortName)
                            .font(.subheadline)
                            .fontWeight(.medium)
                        
                        // Away team ranking
                        if let awayRank = prediction.betSlip.awayRanking {
                            Text("#\(awayRank)")
                                .font(.caption2)
                                .fontWeight(.semibold)
                                .foregroundColor(.black)
                                .padding(.horizontal, 4)
                                .padding(.vertical, 2)
                                .cornerRadius(4)
                        }
                    }
                    
                    // Show away score if game is final
                    if let result = gameResult {
                        Text("\(result.awayScore)")
                            .font(.headline)
                            .fontWeight(.bold)
                            .foregroundColor(result.winner == "away" ? .green : .primary)
                    }
                }
                
                Spacer()
                
                // Versus or @ symbol
                Text(gameResult == nil ? "vs" : "@")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                // Home team
                VStack(spacing: 2) {
                    HStack(spacing: 4) {
                        Text(prediction.homeTeam.shortName)
                            .font(.subheadline)
                            .fontWeight(.medium)
                        
                        // Home team ranking
                        if let homeRank = prediction.betSlip.homeRanking {
                            Text("#\(homeRank)")
                                .font(.caption2)
                                .fontWeight(.semibold)
                                .foregroundColor(.black)
                                .padding(.horizontal, 4)
                                .padding(.vertical, 2)
                                .cornerRadius(4)
                        }
                    }
                    
                    // Show home score if game is final
                    if let result = gameResult {
                        Text("\(result.homeScore)")
                            .font(.headline)
                            .fontWeight(.bold)
                            .foregroundColor(result.winner == "home" ? .green : .primary)
                    }
                }
                
                TeamLogoView(team: prediction.homeTeam, size: 32)
            }
            .padding(.vertical, 2)
        }
        .padding(12)
    }
    
    private var predictionDetailsView: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Divider with better contrast
            Rectangle()
                .fill(Color.gray.opacity(0.3))
                .frame(height: 1)
            
            HStack(alignment: .center) {
                // Bet type and selection
                VStack(alignment: .leading, spacing: 4) {
                    // Sportsbook and odds - MORE PROMINENT
                    HStack(spacing: 4) {
                        Image("sb_\(prediction.bestBet.sportsbook.rawValue.lowercased())")
                            .resizable()
                            .frame(width: 20, height: 20)
                            .cornerRadius(3)
                        
                        Text(prediction.bestBet.sportsbook.displayName)
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(.primary)
                        
                        Text(formatOdds(prediction.bestBet.odds))
                            .font(.subheadline)
                            .fontWeight(.bold)
                            .foregroundColor(.blue)
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(6)
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(Color.blue.opacity(0.3), lineWidth: 1)
                    )
                    
                    Spacer().frame(height: 4)
                    
                    // Bet type
                    Text(getBetTypeText())
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    // Selection
                    Text(prediction.bestBet.selection)
                        .font(.headline)
                        .fontWeight(.semibold)
                }
                
                Spacer()
                
                // Edge Strength indicator (only for upcoming games)
                if gameResult == nil {
                    VStack(spacing: 4) {
                        Text("Edge")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        
                        Text(formatEdge())
                            .font(.subheadline)
                            .fontWeight(.bold)
                            .foregroundColor(.purple)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.purple.opacity(0.1))
                    .cornerRadius(8)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color.purple.opacity(0.3), lineWidth: 1)
                    )
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
        }
    }
    
    // Format edge based on bet type
    private func formatEdge() -> String {
        let edge = edgeStrength
        
        switch prediction.bestBet.type {
        case .moneyline:
            // Show as percentage for moneyline
            return String(format: "%.1f%%", edge)
        case .spread, .total:
            // Show as points for spread/total
            return String(format: "%.1f pts", edge)
        }
    }
    
    // Get the appropriate bet type text
    private func getBetTypeText() -> String {
        switch prediction.bestBet.type {
        case .moneyline:
            return "Moneyline"
        case .spread:
            return "Spread"
        case .total:
            return "Total"
        }
    }
    
    private func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
    
    private func confidenceColor(for probability: Double) -> Color {
        if probability >= 55 {
            return .green
        } else if probability >= 52 {
            return .blue
        } else if probability >= 50 {
            return .orange
        } else {
            return .red
        }
    }
    
    // Color code rankings
    private func rankingColor(for rank: Int) -> Color {
        switch rank {
        case 1...10:
            return .green
        case 11...25:
            return .blue
        case 26...50:
            return .orange
        case 51...100:
            return .purple
        default:
            return .gray
        }
    }
    
    // Format game time as "MM/DD - h:mm a"
    private var formattedDateAndTime: String {
        if let tipoffTime = prediction.betSlip.tipoffTimeString {
            let formatter = DateFormatter()
            formatter.dateFormat = "MM/dd"
            let dateStr = formatter.string(from: prediction.gameTime)
            return "\(dateStr) - \(tipoffTime)"
        } else {
            let formatter = DateFormatter()
            formatter.dateFormat = "MM/dd - h:mm a"
            return formatter.string(from: prediction.gameTime)
        }
    }
}
