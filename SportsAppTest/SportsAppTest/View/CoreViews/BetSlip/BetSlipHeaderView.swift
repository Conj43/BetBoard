//
//  BetSlipHeaderView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/1/25.
//


//
//  BetSlipHeaderView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct BetSlipHeaderView: View {
    let betSlip: BetSlip
    
    var body: some View {
        VStack(spacing: 12) {
            // Game time and venue info
            HStack(spacing: 8) {
                Image(systemName: "calendar")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                
                Text(betSlip.formattedGameTime)
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                if betSlip.neutralSite {
                    Divider()
                        .frame(height: 12)
                    
                    Image(systemName: "location.fill")
                        .font(.caption2)
                        .foregroundColor(.orange)
                    
                    Text("Neutral Site")
                        .font(.caption)
                        .foregroundColor(.orange)
                }
            }
            
            Divider()
                .padding(.horizontal, 20)
            
            // Matchup with team logos
            HStack(spacing: 0) {
                // Away team
                TeamDisplayView(
                    team: betSlip.awayTeam,
                    logoSize: 60
                )
                .frame(maxWidth: .infinity)
                
                // VS / @ Symbol
                VStack(spacing: 4) {
                    Text("@")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.secondary)
                }
                .frame(width: 40)
                
                // Home team
                TeamDisplayView(
                    team: betSlip.homeTeam,
                    logoSize: 60
                )
                .frame(maxWidth: .infinity)
            }
            .padding(.vertical, 8)
            
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
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(Color.blue.opacity(0.1))
                .cornerRadius(6)
            }
        }
        .padding()
        .background(
            LinearGradient(
                gradient: Gradient(colors: [
                    Color(.systemGray6),
                    Color(.systemBackground)
                ]),
                startPoint: .top,
                endPoint: .bottom
            )
        )
    }
}

// MARK: - Team Display View
struct TeamDisplayView: View {
    let team: Team
    let logoSize: CGFloat
    
    var body: some View {
        VStack(spacing: 8) {
            // Team logo
            TeamLogoView(team: team, size: logoSize)
            
            // Team name
            Text(team.shortName)
                .font(.headline)
                .fontWeight(.bold)
            
            // Ranking
            if let ranking = team.ranking {
                Text("#\(ranking)")
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(.blue)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(4)
            }
            
            // Record
            Text("(\(team.record.wins)-\(team.record.losses))")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
}