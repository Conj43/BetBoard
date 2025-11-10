//
//  GameSearchResultRowView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct GameSearchResultRowView: View {
    let betSlip: BetSlip
    
    var body: some View {
        VStack(spacing: 12) {
            // Game header with teams and game time
            HStack {
                // Away team
                TeamLogoView(team: betSlip.awayTeam, size: 36)
                    .padding(.trailing, 4)
                
                VStack(alignment: .leading, spacing: 2) {
                    Text(betSlip.awayTeam.shortName)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    
                    Text("\(betSlip.awayTeam.record.wins)-\(betSlip.awayTeam.record.losses)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                // Game time
                Text(betSlip.formattedGameTime)
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                // Home team
                VStack(alignment: .trailing, spacing: 2) {
                    Text(betSlip.homeTeam.shortName)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    
                    Text("\(betSlip.homeTeam.record.wins)-\(betSlip.homeTeam.record.losses)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                TeamLogoView(team: betSlip.homeTeam, size: 36)
                    .padding(.leading, 4)
            }
            
            // Game tags
            HStack(spacing: 8) {
                // Conference indicator
                if betSlip.homeTeam.conference == betSlip.awayTeam.conference {
                    HStack(spacing: 4) {
                        Image(systemName: "trophy.fill")
                            .font(.caption2)
                        
                        Text(betSlip.homeTeam.conference)
                            .font(.caption)
                            .fontWeight(.medium)
                    }
                    .foregroundColor(.blue)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(6)
                }
                
                // Neutral site indicator
                if betSlip.neutralSite {
                    HStack(spacing: 4) {
                        Image(systemName: "location.fill")
                            .font(.caption2)
                        
                        Text("Neutral")
                            .font(.caption)
                            .fontWeight(.medium)
                    }
                    .foregroundColor(.orange)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.orange.opacity(0.1))
                    .cornerRadius(6)
                }
                
                Spacer()
            }
            
            // Prediction indicators (if available)
            if let predictionInfo = betSlip.predictionInfo {
                VStack(spacing: 8) {
                    // Show individual prediction types
                    
                    if let spreadBet = predictionInfo.spreadBet {
                        PredictionBadgeView(
                            title: "Spread",
                            selection: spreadBet,
                            confidence: predictionInfo.spreadConfidence,
                            iconName: "arrow.up.arrow.down"
                        )
                    }
                    
                    if let totalBet = predictionInfo.totalBet {
                        PredictionBadgeView(
                            title: "Total",
                            selection: totalBet,
                            confidence: predictionInfo.totalConfidence,
                            iconName: "sum"
                        )
                    }
                }
                .padding(.top, 4)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
    }
}

// Helper view for prediction badges
struct PredictionBadgeView: View {
    let title: String
    let selection: String
    let confidence: Double
    let iconName: String
    
    var body: some View {
        HStack {
            // Icon and title
            HStack(spacing: 4) {
                Image(systemName: iconName)
                    .font(.caption2)
                
                Text(title + ":")
                    .font(.caption)
                    .fontWeight(.medium)
            }
            .foregroundColor(.purple)
            
            // Selection
            Text(selection)
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundColor(.primary)
            
            Spacer()
            
            // Confidence
            Text("\(Int(confidence))%")
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(confidenceColor)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 6)
        .background(Color.purple.opacity(0.1))
        .cornerRadius(6)
    }
    
    private var confidenceColor: Color {
        if confidence >= 55 {
            return .green
        } else if confidence >= 50 {
            return .blue
        } else if confidence >= 40 {
            return .orange
        } else {
            return .red
        }
    }
}

#Preview {
    // Create a sample BetSlip for preview
    let sampleBetSlip = BetSlip(
        id: "preview-betslip",
        gameID: "sample-game",
        sportsbook: .draftkings,
        homeTeam: Team(
            id: "home-team",
            name: "Duke Blue Devils",
            shortName: "DUKE",
            logoURL: "",
            record: TeamRecord(wins: 23, losses: 8),
            conference: "ACC",
            ranking: 9,
            colorHex: "#001A57"
        ),
        awayTeam: Team(
            id: "away-team",
            name: "North Carolina Tar Heels",
            shortName: "UNC",
            logoURL: "",
            record: TeamRecord(wins: 21, losses: 10),
            conference: "ACC",
            ranking: 15,
            colorHex: "#4B9CD3"
        ),
        gameTime: Date(),
        bettingLines: BettingLines(
            id: "preview-lines",
            gameID: "sample-game",
            moneyline: ["DUKE": -150, "UNC": 130],
            spread: ["DUKE -3.5": -110, "UNC +3.5": -110],
            total: ["Over 145.5": -110, "Under 145.5": -110]
        ),
        allBettingLines: nil,
        predictionInfo: PredictionInfo(
            spreadConfidence: 85.0,
            spreadBet: "UNC +3.5",
            totalConfidence: 65.0,
            totalBet: "OVER 145.5",
            analysis: "Strong defensive matchup favors the underdog"
        ),
        neutralSite: false
    )
    
    GameSearchResultRowView(betSlip: sampleBetSlip)
        .previewLayout(.sizeThatFits)
        .padding()
}
