//
//  PredictionRowView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


import SwiftUI

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
