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
            
            // Prediction details
            predictionDetailsView
        }
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
        .padding(.bottom, 4)
    }
    
    private var gameHeaderView: some View {
        VStack(spacing: 8) {
            HStack {
                // Game time
                Text(prediction.formattedGameTime)
                    .font(.footnote)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                // Confidence indicator based on win probability
                HStack(spacing: 4) {
                    Image(systemName: "chart.bar.fill")
                        .font(.caption2)
                    
                    Text("\(Int(winProbability))% Win Probability")
                        .font(.caption)
                        .fontWeight(.medium)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(confidenceColor(for: winProbability).opacity(0.1))
                .foregroundColor(confidenceColor(for: winProbability))
                .cornerRadius(8)
            }
            
            // Team matchup
            HStack(alignment: .center, spacing: 8) {
                // Away team
                TeamLogoView(team: prediction.awayTeam, size: 36)
                
                Text(prediction.awayTeam.shortName)
                    .font(.subheadline)
                    .fontWeight(.medium)
                
                Spacer()
                
                // Versus
                Text("vs")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                // Home team
                Text(prediction.homeTeam.shortName)
                    .font(.subheadline)
                    .fontWeight(.medium)
                
                TeamLogoView(team: prediction.homeTeam, size: 36)
            }
            .padding(.vertical, 2)
        }
        .padding(12)
    }
    
    private var predictionDetailsView: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Divider
            Rectangle()
                .fill(Color.secondary.opacity(0.2))
                .frame(height: 1)
            
            HStack(alignment: .center) {
                // Bet type and selection
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(getBetTypeText())
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        Spacer()
                        
                        // Sportsbook and odds
                        HStack(spacing: 4) {
                            Text(prediction.bestBet.sportsbook.displayName)
                                .font(.caption)
                                .foregroundColor(.secondary)
                            
                            Text(formatOdds(prediction.bestBet.odds))
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Text(prediction.bestBet.selection)
                        .font(.headline)
                        .fontWeight(.semibold)
                }
                
                Spacer()
                
                // Edge Strength indicator - display as points
                Text("Edge: \(String(format: "%.1f", edgeStrength))")
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.purple.opacity(0.1))
                    .foregroundColor(.purple)
                    .cornerRadius(8)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
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
}
