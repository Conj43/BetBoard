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
            // Top row: Matchup with logos
            HStack(spacing: 12) {
                // Away team section
                HStack(spacing: 8) {
                    // Away team logo
                    TeamLogoView(team: betSlip.awayTeam, size: 32)
                    
                    VStack(alignment: .leading, spacing: 2) {
                        HStack(spacing: 4) {
                            if let ranking = betSlip.awayTeam.ranking {
                                Text("#\(ranking)")
                                    .font(.caption2)
                                    .fontWeight(.bold)
                                    .foregroundColor(.blue)
                            }
                            
                            Text(betSlip.awayTeam.shortName)
                                .font(.subheadline)
                                .fontWeight(.semibold)
                                .lineLimit(1)
                        }
                        
                        Text("(\(betSlip.awayTeam.record.wins)-\(betSlip.awayTeam.record.losses))")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                
                // @ symbol
                Text("@")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 4)
                
                // Home team section
                HStack(spacing: 8) {
                    VStack(alignment: .leading, spacing: 2) {
                        HStack(spacing: 4) {
                            if let ranking = betSlip.homeTeam.ranking {
                                Text("#\(ranking)")
                                    .font(.caption2)
                                    .fontWeight(.bold)
                                    .foregroundColor(.blue)
                            }
                            
                            Text(betSlip.homeTeam.shortName)
                                .font(.subheadline)
                                .fontWeight(.semibold)
                                .lineLimit(1)
                        }
                        
                        Text("(\(betSlip.homeTeam.record.wins)-\(betSlip.homeTeam.record.losses))")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    
                    // Home team logo
                    TeamLogoView(team: betSlip.homeTeam, size: 32)
                }
                
                Spacer()
                
                // Chevron
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            // Bottom row: Game time and conference
            HStack {
                // Game time
                HStack(spacing: 4) {
                    Image(systemName: "calendar")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                    
                    Text(betSlip.formattedGameTime)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                // Conference badge (if same conference)
                if betSlip.homeTeam.conference == betSlip.awayTeam.conference {
                    HStack(spacing: 4) {
                        Image(systemName: "shield.fill")
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
            }
            
            // Prediction indicator (if available)
            if let predictionInfo = betSlip.predictionInfo,
               let recommendedBet = predictionInfo.recommendedBet {
                HStack(spacing: 6) {
                    Image(systemName: "brain.head.profile")
                        .font(.caption2)
                        .foregroundColor(.purple)
                    
                    Text("Prediction: \(recommendedBet)")
                        .font(.caption)
                        .foregroundColor(.purple)
                        .fontWeight(.medium)
                    
                    Spacer()
                    
                    Text("\(Int(predictionInfo.confidence))% confidence")
                        .font(.caption2)
                        .foregroundColor(.purple)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.purple.opacity(0.1))
                        .cornerRadius(4)
                }
                .padding(.top, 4)
            }
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
