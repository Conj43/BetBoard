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
        HStack(spacing: 12) {
            // Away team info
            HStack(spacing: 8) {
                if let ranking = betSlip.awayTeam.ranking {
                    Text("#\(ranking)")
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundColor(.blue)
                }
                
                Text(betSlip.awayTeam.shortName)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                
                Text("(\(betSlip.awayTeam.record.wins)-\(betSlip.awayTeam.record.losses))")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            // @ symbol
            Text("@")
                .font(.subheadline)
                .foregroundColor(.secondary)
            
            // Home team info
            HStack(spacing: 8) {
                if let ranking = betSlip.homeTeam.ranking {
                    Text("#\(ranking)")
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundColor(.blue)
                }
                
                Text(betSlip.homeTeam.shortName)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                
                Text("(\(betSlip.homeTeam.record.wins)-\(betSlip.homeTeam.record.losses))")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            // Game time and conference
            VStack(alignment: .trailing, spacing: 4) {
                Text(betSlip.formattedGameTime)
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                if betSlip.homeTeam.conference == betSlip.awayTeam.conference {
                    Text(betSlip.homeTeam.conference)
                        .font(.caption)
                        .foregroundColor(.blue)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.blue.opacity(0.1))
                        .cornerRadius(4)
                }
            }
            
            // Chevron
            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 2, x: 0, y: 1)
        .foregroundColor(.primary)
    }
}

#Preview {
    // Create a sample BetSlip for preview with correct initializers
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
        allBettingLines: nil, // No multiple sportsbooks for this preview
        predictionInfo: PredictionInfo(
            confidence: 85.0,
            recommendedBet: "UNC +3.5",
            analysis: "Strong defensive matchup favors the underdog"
        ),
        neutralSite: false
    )
    
    GameSearchResultRowView(betSlip: sampleBetSlip)
        .padding()
}
